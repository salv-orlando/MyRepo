# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Citrix Systems
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


LOG = logging.getLogger('quantum.api.views.filters')


def _load_network_ports_details(network, plugin, tenant_id):
    if not 'net-ports' in network:
        port_list = plugin.get_all_ports(tenant_id, network['net-id'])
        ports_data = [plugin.get_port_details(
                                   tenant_id, network['net-id'],
                                   port['port-id'])
                      for port in port_list]
        network['net-ports'] = ports_data


def _filter_network_by_name(network, name, **kwargs):
    if not 'net-name' in network:
        return False
    return network['net-name'] == name


def _filter_network_with_operational_port(network, port_op_status,
                                          **kwargs):
    plugin = kwargs.get('plugin', None)
    tenant_id = kwargs.get('tenant_id', None)
    if not plugin or not tenant_id:
        return False # This should never happen
    #load network details if required
    _load_network_ports_details(network, plugin, tenant_id)
    return any([port['port-op-status'] == port_op_status
                for port in network['net-ports']])


def _filter_network_with_active_port(network, port_state, **kwargs):
    plugin = kwargs.get('plugin', None)
    tenant_id = kwargs.get('tenant_id', None)
    if not plugin or not tenant_id:
        return False # This should never happen
    #load network details if required
    _load_network_ports_details(network, plugin, tenant_id)
    return any([port['port-state'] == port_state
                for port in network['net-ports']])


def _filter_network_has_interface(network, has_interface, **kwargs):
    plugin = kwargs.get('plugin', None)
    tenant_id = kwargs.get('tenant_id', None)
    if not plugin or not tenant_id:
        return False # This should never happen
    #load network details if required
    _load_network_ports_details(network, plugin, tenant_id)
    # convert to bool
    if has_interface.lower() == 'true':
        has_interface = True
    else:
        has_interface = False
    if has_interface:
        result = any([port['attachment'] is not None
                      for port in network['net-ports']])
    else:
        result = all([port['attachment'] is None
                      for port in network['net-ports']])        
    return result


def _filter_network_by_port(network, port_id, **kwargs):
    plugin = kwargs.get('plugin', None)
    tenant_id = kwargs.get('tenant_id', None)
    if not plugin or not tenant_id:
        return False # This should never happen
    #load network details if required
    _load_network_ports_details(network, plugin, tenant_id)
    return any([port['port-id'] == port_id
                for port in network['net-ports']])


def _filter_network_by_interface(network, interface_id, **kwargs):
    plugin = kwargs.get('plugin', None)
    tenant_id = kwargs.get('tenant_id', None)
    if not plugin or not tenant_id:
        return False # This should never happen
    #load network details if required
    _load_network_ports_details(network, plugin, tenant_id)
    return any([port['attachment'] == interface_id
                for port in network['net-ports']])


def _filter_port_by_state(port, state, **kwargs):
    if not 'port-state' in port:
        return False
    return port['port-state'] == state


def _filter_network_by_op_status(network, op_status, **kwargs):
    if not 'net-op-status' in network:
        return False
    return network['net-op-status'] == op_status


def _filter_port_by_op_status(port, op_status, **kwargs):
    if not 'net-op-status' in port:
        return False
    return port['port-op-status'] == op_status


def _filter_port_by_interface(port, interface_id, **kwargs):
    if not 'attachment' in port:
        return False
    return port['attachment'] == interface_id


def _filter_port_has_interface(port, has_interface, **kwargs):
    # convert to bool
    if has_interface.lower() == 'true':
        has_interface = True
    else:
        has_interface = False
    if not 'attachment' in port or port['attachment'] == None:
        return not has_interface
    return has_interface


def filter_networks(networks, plugin, tenant_id, filter_opts):
    filtered_networks = []
    # load filter functions
    filters = {
        'name': _filter_network_by_name,
        'op-status': _filter_network_by_op_status,
        'has-operational-port': _filter_network_with_operational_port, 
        'has-active-port': _filter_network_with_active_port,
        'has-interface': _filter_network_has_interface,
        'with-interface': _filter_network_by_interface,
        'with-port': _filter_network_by_port}
    # iterate over networks
    for network in networks:
        result = False
        LOG.debug("network:%s", network)
        for flt in filters:
            LOG.debug("filter:%s", flt)
            if flt in filter_opts:
                result = filters[flt](network, filter_opts[flt],
                                      plugin=plugin, tenant_id=tenant_id)
                LOG.debug("result:%s", result)
                if not result:
                    break
        if result:
            filtered_networks.append(network)
    return filtered_networks


def filter_ports(ports, plugin, tenant_id, network_id, filter_opts):
    filtered_ports = []
    # load filter functions
    filters = {
        'state': _filter_port_by_state,
        'op-status': _filter_port_by_op_status,
        'has-interface': _filter_port_has_interface,
        'with-interface': _filter_port_by_interface}
    # iterate over networks
    for port in ports:
        result = False
        port = plugin.get_port_details(tenant_id, network_id,
                                       port['port-id'])
        LOG.debug("port:%s", port)
        for flt in filters:
            LOG.debug("filter:%s", flt)
            if flt in filter_opts:
                # Pass plugin, network_id, and tenant_id to filters anyway
                # even though the ones currently defined do not use them
                result = filters[flt](port, filter_opts[flt],
                                      plugin=plugin,
                                      network_id=network_id,
                                      tenant_id=tenant_id)
                LOG.debug("result:%s", result)
                if not result:
                    break
        if result:
            filtered_ports.append(port)
    return filtered_ports