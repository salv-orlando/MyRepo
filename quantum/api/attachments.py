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
from quantum.api.views import attachments as attachments_view
from quantum.common import exceptions as exception
from quantum.common import wsgi

LOG = logging.getLogger('quantum.api.ports')


def create_resource(plugin, version):
    controller_dict = {
                        '1.0': [ControllerV10(plugin),
                               ControllerV10._serialization_metadata,
                               common.XML_NS_V10],
                        '1.1': [ControllerV11(plugin),
                                ControllerV11._serialization_metadata,
                                common.XML_NS_V11]}
    return common.create_resource(version, controller_dict)    


class Controller(common.QuantumController):
    """ Port API controller for Quantum API """

    _attachment_ops_param_list = [{
        'param-name': 'id',
        'required': True}, ]

    _serialization_metadata = {
        "application/xml": {
            "attributes": {
                "attachment": ["id"], }
        },
    }

    def __init__(self, plugin):
        self._resource_name = 'attachment'
        super(Controller, self).__init__(plugin)

    def get_resource(self, request, tenant_id, network_id, id):
        try:
            att_data = self._plugin.get_port_details(
                            tenant_id, network_id, id)
            builder = attachments_view.get_view_builder(request)
            result = builder.build(att_data)['attachment']
            return dict(attachment=result)
        except exception.NetworkNotFound as e:
            return wsgi.Fault(faults.NetworkNotFound(e))
        except exception.PortNotFound as e:
            return wsgi.Fault(faults.PortNotFound(e))

    def attach_resource(self, request, tenant_id, network_id, id):
        try:
            request_params = \
                self._parse_request_params(request,
                                           self._attachment_ops_param_list)
        except exc.HTTPError as e:
            return wsgi.Fault(e)
        try:
            LOG.debug("PLUGGING INTERFACE:%s", request_params['id'])
            self._plugin.plug_interface(tenant_id, network_id, id,
                                        request_params['id'])
            return exc.HTTPNoContent()
        except exception.NetworkNotFound as e:
            return wsgi.Fault(faults.NetworkNotFound(e))
        except exception.PortNotFound as e:
            return wsgi.Fault(faults.PortNotFound(e))
        except exception.PortInUse as e:
            return wsgi.Fault(faults.PortInUse(e))
        except exception.AlreadyAttached as e:
            return wsgi.Fault(faults.AlreadyAttached(e))

    def detach_resource(self, request, tenant_id, network_id, id):
        try:
            self._plugin.unplug_interface(tenant_id,
                                          network_id, id)
            return exc.HTTPNoContent()
        except exception.NetworkNotFound as e:
            return wsgi.Fault(faults.NetworkNotFound(e))
        except exception.PortNotFound as e:
            return wsgi.Fault(faults.PortNotFound(e))
        
        


class ControllerV10(Controller):
    
    def __init__(self, plugin):
        self.version = "1.0"
        super(ControllerV10, self).__init__(plugin)


class ControllerV11(Controller):
    
    def __init__(self, plugin):
        self.version = "1.1"
        super(ControllerV11, self).__init__(plugin)
