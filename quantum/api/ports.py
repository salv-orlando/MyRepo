# Copyright 2011 Citrix Systems.
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

import logging

from webob import exc

from quantum.api import api_common as common
from quantum.api import faults
from quantum.api.views import ports as ports_view
from quantum.common import exceptions as exception

LOG = logging.getLogger('quantum.api.ports')

class Controller(common.QuantumController):
    """ Port API controller for Quantum API """

    _port_ops_param_list = [{
        'param-name': 'port-state',
        'default-value': 'DOWN',
        'required': False},]

    _attachment_ops_param_list = [{
        'param-name': 'attachment-id',
        'required': True},]

    _serialization_metadata = {
        "application/xml": {
            "attributes": {
                "port": ["id","state"],
            },
        },
    }

    def __init__(self, plugin_conf_file=None):
        self._resource_name = 'port'
        super(Controller, self).__init__()

    def index(self, req, tenant_id, network_id):
        """ Returns a list of port ids for a given network """
        return self._items(req, tenant_id, network_id, is_detail=False)

    def _items(self, req, tenant_id, network_id, is_detail):
        """ Returns a list of networks. """
        try :
            ports = self.network_manager.get_all_ports(tenant_id, network_id)
            builder = ports_view.get_view_builder(req)
            result = [builder.build(port, is_detail)['port']
                      for port in ports]
            return dict(ports=result)
        except exception.NetworkNotFound as e:
            return faults.Fault(faults.NetworkNotFound(e))

    def show(self, req, tenant_id, network_id, id):
        """ Returns port details for given port and network """
        try:
            port = self.network_manager.get_port_details(
                            tenant_id, network_id, id)
            builder = ports_view.get_view_builder(req)
            #build response with details
            result = builder.build(port, True)
            return dict(ports=result)
        except exception.NetworkNotFound as e:
            return faults.Fault(faults.NetworkNotFound(e))
        except exception.PortNotFound as e:
            return faults.Fault(faults.PortNotFound(e))

    def create(self, req, tenant_id, network_id):
        """ Creates a new port for a given network """
        #look for port state in request
        try:
            req_params = \
                self._parse_request_params(req, self._port_ops_param_list)
        except exc.HTTPError as e:
            return faults.Fault(e)
        try:
            port = self.network_manager.create_port(tenant_id,
                                                    network_id,
                                                    req_params['port-state'])
            builder = ports_view.get_view_builder(req)
            result = builder.build(port)
            return dict(ports=result)
        except exception.NetworkNotFound as e:
            return faults.Fault(faults.NetworkNotFound(e))
        except exception.StateInvalid as e:
            return faults.Fault(faults.RequestedStateInvalid(e))

    def update(self, req, tenant_id, network_id, id):
        """ Updates the state of a port for a given network """
        #look for port state in request
        try:
            req_params = \
                self._parse_request_params(req, self._port_ops_param_list)
        except exc.HTTPError as e:
            return faults.Fault(e)
        try:
            port = self.network_manager.update_port(tenant_id,network_id, id,
                                                    req_params['port-state'])
            builder = ports_view.get_view_builder(req)
            result = builder.build(port, True)
            return dict(ports=result)
        except exception.NetworkNotFound as e:
            return faults.Fault(faults.NetworkNotFound(e))
        except exception.PortNotFound as e:
            return faults.Fault(faults.PortNotFound(e))
        except exception.StateInvalid as e:
            return faults.Fault(faults.RequestedStateInvalid(e))

    def delete(self, req, tenant_id, network_id, id):
        """ Destroys the port with the given id """
        #look for port state in request
        try:
            self.network_manager.delete_port(tenant_id, network_id, id)
            return exc.HTTPAccepted()
            #TODO(salvatore-orlando): Handle portInUse error
        except exception.NetworkNotFound as e:
            return faults.Fault(faults.NetworkNotFound(e))
        except exception.PortNotFound as e:
            return faults.Fault(faults.PortNotFound(e))
        except exception.PortInUse as e:
            return faults.Fault(faults.PortInUse(e))

    def get_resource(self,req,tenant_id, network_id, id):
        try:
            result = self.network_manager.get_interface_details(
                            tenant_id, network_id, id)
            return dict(attachment=result)
        except exception.NetworkNotFound as e:
            return faults.Fault(faults.NetworkNotFound(e))
        except exception.PortNotFound as e:
            return faults.Fault(faults.PortNotFound(e))

    #TODO - Complete implementation of these APIs
    def attach_resource(self,req,tenant_id, network_id, id):
        content_type = req.best_match_content_type()
        print "Content type:%s" %content_type
        try:
            req_params = \
                self._parse_request_params(req,
                                           self._attachment_ops_param_list)
        except exc.HTTPError as e:
            return faults.Fault(e)
        try:
            self.network_manager.plug_interface(tenant_id,
                                                network_id,id,
                                                req_params['attachment-id'])
            return exc.HTTPAccepted()
        except exception.NetworkNotFound as e:
            return faults.Fault(faults.NetworkNotFound(e))
        except exception.PortNotFound as e:
            return faults.Fault(faults.PortNotFound(e))
        except exception.PortInUse as e:
            return faults.Fault(faults.PortInUse(e))
        except exception.AlreadyAttached as e:
            return faults.Fault(faults.AlreadyAttached(e))

    #TODO - Complete implementation of these APIs
    def detach_resource(self,req,tenant_id, network_id, id):
        try:
            self.network_manager.unplug_interface(tenant_id,
                                                  network_id,id)
            return exc.HTTPAccepted()
        except exception.NetworkNotFound as e:
            return faults.Fault(faults.NetworkNotFound(e))
        except exception.PortNotFound as e:
            return faults.Fault(faults.PortNotFound(e))