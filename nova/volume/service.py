# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Nova Storage manages creating, attaching, detaching, and
destroying persistent storage volumes, ala EBS.
Currently uses Ata-over-Ethernet.
"""

import glob
import logging
import os
import shutil
import socket
import tempfile

from twisted.internet import defer

from nova import datastore
from nova import exception
from nova import flags
from nova import process
from nova import service
from nova import utils
from nova import validate


FLAGS = flags.FLAGS
flags.DEFINE_string('storage_dev', '/dev/sdb',
                    'Physical device to use for volumes')
flags.DEFINE_string('volume_group', 'nova-volumes',
                    'Name for the VG that will contain exported volumes')
flags.DEFINE_string('aoe_eth_dev', 'eth0',
                    'Which device to export the volumes on')
flags.DEFINE_string('storage_name',
                    socket.gethostname(),
                    'name of this service')
flags.DEFINE_integer('first_shelf_id',
                    utils.last_octet(utils.get_my_ip()) * 10,
                    'AoE starting shelf_id for this service')
flags.DEFINE_integer('last_shelf_id',
                    utils.last_octet(utils.get_my_ip()) * 10 + 9,
                    'AoE starting shelf_id for this service')
flags.DEFINE_string('aoe_export_dir',
                    '/var/lib/vblade-persist/vblades',
                    'AoE directory where exports are created')
flags.DEFINE_integer('slots_per_shelf',
                    16,
                    'Number of AoE slots per shelf')
flags.DEFINE_string('storage_availability_zone',
                    'nova',
                    'availability zone of this service')
flags.DEFINE_boolean('fake_storage', False,
                     'Should we make real storage volumes to attach?')


class NoMoreVolumes(exception.Error):
    pass

def get_volume(volume_id):
    """ Returns a redis-backed volume object """
    volume_class = Volume
    if FLAGS.fake_storage:
        volume_class = FakeVolume
    if datastore.Redis.instance().sismember('volumes', volume_id):
        return volume_class(volume_id=volume_id)
    raise exception.Error("Volume does not exist")

class VolumeService(service.Service):
    """
    There is one VolumeNode running on each host.
    However, each VolumeNode can report on the state of
    *all* volumes in the cluster.
    """
    def __init__(self):
        super(VolumeService, self).__init__()
        self.volume_class = Volume
        if FLAGS.fake_storage:
            FLAGS.aoe_export_dir = tempfile.mkdtemp()
            self.volume_class = FakeVolume
        self._init_volume_group()

    def __del__(self):
        # TODO(josh): Get rid of this destructor, volumes destroy themselves
        if FLAGS.fake_storage:
            try:
                shutil.rmtree(FLAGS.aoe_export_dir)
            except Exception, err:
                pass

    @defer.inlineCallbacks
    @validate.rangetest(size=(0, 1000))
    def create_volume(self, size, user_id, project_id):
        """
        Creates an exported volume (fake or real),
        restarts exports to make it available.
        Volume at this point has size, owner, and zone.
        """
        logging.debug("Creating volume of size: %s" % (size))
        vol = yield self.volume_class.create(size, user_id, project_id)
        datastore.Redis.instance().sadd('volumes', vol['volume_id'])
        datastore.Redis.instance().sadd('volumes:%s' % (FLAGS.storage_name), vol['volume_id'])
        logging.debug("restarting exports")
        yield self._restart_exports()
        defer.returnValue(vol['volume_id'])

    def by_node(self, node_id):
        """ returns a list of volumes for a node """
        for volume_id in datastore.Redis.instance().smembers('volumes:%s' % (node_id)):
            yield self.volume_class(volume_id=volume_id)

    @property
    def all(self):
        """ returns a list of all volumes """
        for volume_id in datastore.Redis.instance().smembers('volumes'):
            yield self.volume_class(volume_id=volume_id)

    @defer.inlineCallbacks
    def delete_volume(self, volume_id):
        logging.debug("Deleting volume with id of: %s" % (volume_id))
        vol = get_volume(volume_id)
        if vol['status'] == "attached":
            raise exception.Error("Volume is still attached")
        if vol['node_name'] != FLAGS.storage_name:
            raise exception.Error("Volume is not local to this node")
        yield vol.destroy()
        datastore.Redis.instance().srem('volumes', vol['volume_id'])
        datastore.Redis.instance().srem('volumes:%s' % (FLAGS.storage_name), vol['volume_id'])
        defer.returnValue(True)

    @defer.inlineCallbacks
    def _restart_exports(self):
        if FLAGS.fake_storage:
            return
        yield process.simple_execute("sudo vblade-persist auto all")
        # NOTE(vish): this command sometimes sends output to stderr for warnings
        yield process.simple_execute("sudo vblade-persist start all", error_ok=1)

    @defer.inlineCallbacks
    def _init_volume_group(self):
        if FLAGS.fake_storage:
            return
        yield process.simple_execute(
                "sudo pvcreate %s" % (FLAGS.storage_dev))
        yield process.simple_execute(
                "sudo vgcreate %s %s" % (FLAGS.volume_group,
                                         FLAGS.storage_dev))

class Volume(datastore.BasicModel):

    def __init__(self, volume_id=None):
        self.volume_id = volume_id
        super(Volume, self).__init__()

    @property
    def identifier(self):
        return self.volume_id

    def default_state(self):
        return {"volume_id": self.volume_id}

    @classmethod
    @defer.inlineCallbacks
    def create(cls, size, user_id, project_id):
        volume_id = utils.generate_uid('vol')
        vol = cls(volume_id)
        vol['node_name'] = FLAGS.storage_name
        vol['size'] = size
        vol['user_id'] = user_id
        vol['project_id'] = project_id
        vol['availability_zone'] = FLAGS.storage_availability_zone
        vol["instance_id"] = 'none'
        vol["mountpoint"] = 'none'
        vol['attach_time'] = 'none'
        vol['status'] = "creating" # creating | available | in-use
        vol['attach_status'] = "detached"  # attaching | attached | detaching | detached
        vol['delete_on_termination'] = 'False'
        vol.save()
        yield vol._create_lv()
        yield vol._setup_export()
        # TODO(joshua) - We need to trigger a fanout message for aoe-discover on all the nodes
        vol['status'] = "available"
        vol.save()
        defer.returnValue(vol)

    def start_attach(self, instance_id, mountpoint):
        """ """
        self['instance_id'] = instance_id
        self['mountpoint'] = mountpoint
        self['status'] = "in-use"
        self['attach_status'] = "attaching"
        self['attach_time'] = utils.isotime()
        self['delete_on_termination'] = 'False'
        self.save()

    def finish_attach(self):
        """ """
        self['attach_status'] = "attached"
        self.save()

    def start_detach(self):
        """ """
        self['attach_status'] = "detaching"
        self.save()

    def finish_detach(self):
        self['instance_id'] = None
        self['mountpoint'] = None
        self['status'] = "available"
        self['attach_status'] = "detached"
        self.save()

    @defer.inlineCallbacks
    def destroy(self):
        try:
            yield self._remove_export()
        except Exception as ex:
            logging.debug("Ingnoring failure to remove export %s" % ex)
            pass
        yield self._delete_lv()
        super(Volume, self).destroy()

    @defer.inlineCallbacks
    def _create_lv(self):
        if str(self['size']) == '0':
            sizestr = '100M'
        else:
            sizestr = '%sG' % self['size']
        yield process.simple_execute(
                "sudo lvcreate -L %s -n %s %s" % (sizestr,
                                                  self['volume_id'],
                                                  FLAGS.volume_group))

    @defer.inlineCallbacks
    def _delete_lv(self):
        yield process.simple_execute(
                "sudo lvremove -f %s/%s" % (FLAGS.volume_group,
                                            self['volume_id']))

    @defer.inlineCallbacks
    def _setup_export(self):
        (shelf_id, blade_id) = get_next_aoe_numbers()
        self['aoe_device'] = "e%s.%s" % (shelf_id, blade_id)
        self['shelf_id'] = shelf_id
        self['blade_id'] = blade_id
        self.save()
        yield self._exec_export()

    @defer.inlineCallbacks
    def _exec_export(self):
        yield process.simple_execute(
                "sudo vblade-persist setup %s %s %s /dev/%s/%s" %
                (self['shelf_id'],
                 self['blade_id'],
                 FLAGS.aoe_eth_dev,
                 FLAGS.volume_group,
                 self['volume_id']))

    @defer.inlineCallbacks
    def _remove_export(self):
        yield process.simple_execute(
                "sudo vblade-persist stop %s %s" % (self['shelf_id'],
                                                    self['blade_id']))
        yield process.simple_execute(
                "sudo vblade-persist destroy %s %s" % (self['shelf_id'],
                                                       self['blade_id']))


class FakeVolume(Volume):
    def _create_lv(self):
        pass

    def _exec_export(self):
        fname = os.path.join(FLAGS.aoe_export_dir, self['aoe_device'])
        f = file(fname, "w")
        f.close()

    def _remove_export(self):
        pass

    def _delete_lv(self):
        pass

def get_next_aoe_numbers():
    for shelf_id in xrange(FLAGS.first_shelf_id, FLAGS.last_shelf_id + 1):
        aoes = glob.glob("%s/e%s.*" % (FLAGS.aoe_export_dir, shelf_id))
        if not aoes:
            blade_id = 0
        else:
            blade_id = int(max([int(a.rpartition('.')[2]) for a in aoes])) + 1
        if blade_id < FLAGS.slots_per_shelf:
            logging.debug("Next shelf.blade is %s.%s", shelf_id, blade_id)
            return (shelf_id, blade_id)
    raise NoMoreVolumes()