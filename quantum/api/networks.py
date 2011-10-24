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
from quantum.api.views import networks as networks_view
from quantum.common import exceptions as exception
from quantum.common import wsgi

LOG = logging.getLogger('quantum.api.networks')


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
    """ Network API controller for Quantum API """

    _network_ops_param_list = [{
        'param-name': 'name',
        'required': True}, ]

    _serialization_metadata = {
            "attributes": {
                "network": ["id", "name"],
                "port": ["id", "state"],
                "attachment": ["id"]},
            "plurals": {"networks": "network",
                        "ports": "port"}
    }

    def __init__(self, plugin):
        self._resource_name = 'network'
        super(Controller, self).__init__(plugin)

    def _item(self, request, tenant_id, network_id,
              net_details=True, port_details=False):
        # We expect get_network_details to return information
        # concerning logical ports as well.
        network = self._plugin.get_network_details(
                            tenant_id, network_id)
        port_list = self._plugin.get_all_ports(
                            tenant_id, network_id)
        ports_data = [self._plugin.get_port_details(
                                   tenant_id, network_id, port['port-id'])
                      for port in port_list]
        builder = networks_view.get_view_builder(request, self.version)
        result = builder.build(network, net_details,
                               ports_data, port_details)['network']
        return dict(network=result)

    def _items(self, request, tenant_id, net_details=False):
        """ Returns a list of networks. """
        networks = self._plugin.get_all_networks(tenant_id)
        builder = networks_view.get_view_builder(request, self.version)
        result = [builder.build(network, net_details)['network']
                  for network in networks]
        return dict(networks=result)

    def index(self, request, tenant_id):
        """ Returns a list of network ids """
        return self._items(request, tenant_id)

    def show(self, request, tenant_id, id):
        """ Returns network details for the given network id """
        try:
            return self._item(request, tenant_id, id,
                              net_details=True, port_details=False)
        except exception.NetworkNotFound as e:
            return faults.NetworkNotFound(e)

    def detail(self, request, **kwargs):
        tenant_id = kwargs.get('tenant_id')
        network_id = kwargs.get('id')
        if network_id:
            # show details for a given network
            return self._item(request, tenant_id, network_id,
                              net_details=True, port_details=True)
        else:
            # show details for all networks
            return self._items(request, tenant_id, net_details=True)

    def create(self, request, tenant_id, body):
        """ Creates a new network for a given tenant """
        body = self._prepare_request_body(body, self._network_ops_param_list)
        network = self._plugin.\
                   create_network(tenant_id,
                                  body['network']['name'])
        builder = networks_view.get_view_builder(request, self.version)
        result = builder.build(network)['network']
        return dict(network=result)

    def update(self, request, tenant_id, id, body):
        """ Updates the name for the network with the given id """
        body = self._prepare_request_body(body, self._network_ops_param_list)
        try:
            self._plugin.rename_network(tenant_id, id, body['network']['name'])
        except exception.NetworkNotFound as e:
            return faults.NetworkNotFound(e)

    def delete(self, request, tenant_id, id):
        """ Destroys the network with the given id """
        try:
            self._plugin.delete_network(tenant_id, id)
            # no need anymore for returning exc.HTTPNoContent()
        except exception.NetworkNotFound as e:
            return faults.NetworkNotFound(e)
        except exception.NetworkInUse as e:
            return faults.NetworkInUse(e)


class ControllerV10(Controller):

    def __init__(self, plugin):
        self.version = "1.0"
        super(ControllerV10, self).__init__(plugin)


class ControllerV11(Controller):

    def __init__(self, plugin):
        self.version = "1.1"
        super(ControllerV11, self).__init__(plugin)
