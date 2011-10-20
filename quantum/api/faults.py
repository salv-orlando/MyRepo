# vim: tabstop=4 shiftwidth=4 softtabstop=4

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


import webob.exc


class NetworkNotFound(webob.exc.HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the server did not find the network specified
    in the HTTP request

    code: 420, title: Network not Found
    """
    code = 420
    title = 'Network not Found'
    explanation = ('Unable to find a network with the specified identifier.')


class NetworkInUse(webob.exc.HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the server could not delete the network as there is
    at least an attachment plugged into its ports

    code: 421, title: Network In Use
    """
    code = 421
    title = 'Network in Use'
    explanation = ('Unable to remove the network: attachments still plugged.')


class PortNotFound(webob.exc.HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the server did not find the port specified
    in the HTTP request for a given network

    code: 430, title: Port not Found
    """
    code = 430
    title = 'Port not Found'
    explanation = ('Unable to find a port with the specified identifier.')


class RequestedStateInvalid(webob.exc.HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the server could not update the port state to
    to the request value

    code: 431, title: Requested State Invalid
    """
    code = 431
    title = 'Requested State Invalid'
    explanation = ('Unable to update port state with specified value.')


class PortInUse(webob.exc.HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the server could not remove o port or attach
    a resource to it because there is an attachment plugged into the port

    code: 432, title: PortInUse
    """
    code = 432
    title = 'Port in Use'
    explanation = ('A resource is currently attached to the logical port')


class AlreadyAttached(webob.exc.HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the server refused an attempt to re-attach a resource
    already attached to the network

    code: 440, title: AlreadyAttached
    """
    code = 440
    title = 'Already Attached'
    explanation = ('The resource is already attached to another port')
