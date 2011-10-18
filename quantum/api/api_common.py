# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2011 Citrix System.
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
import webob

from webob import exc
from quantum.common import wsgi

XML_NS_V01 = 'http://netstack.org/quantum/api/v0.1'
XML_NS_V10 = 'http://netstack.org/quantum/api/v1.0'
XML_NS_V11 = 'http://netstack.org/quantum/api/v1.1'
LOG = logging.getLogger('quantum.api.api_common')


class HeadersSerializer(wsgi.ResponseHeadersSerializer):
    """ 
    Defines default respone status codes for Quantum API operations
        create - 202 ACCEPTED
        update - 204 NOCONTENT
        delete - 204 NOCONTENT
        others - 200 OK (defined in base class)
        
    """ 

    def create(self, response, data):
        response.status_int = 202

    def delete(self, response, data):
        response.status_int = 204

    def action(self, response, data):
        response.status_int = 202
        
        
class QuantumController(wsgi.Controller):
    """ Base controller class for Quantum API """

    def __init__(self, plugin):
        self._plugin = plugin
        super(QuantumController, self).__init__()