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


def create_resource(version, controller_dict):
    """
    Generic function for creating a wsgi resource
    The function takes as input:
     - desired version
     - controller and metadata dictionary
       e.g.: {'1.0': [ctrl_v10, meta_v10, xml_ns],
              '1.1': [ctrl_v11, meta_v11, xml_ns]}
     
    """
    # the first element of the iterable is expected to be the controller
    controller = controller_dict[version][0]
    # the second element should be the metadata
    metadata = controller_dict[version][1]
    # and the third element the xml namespace
    xmlns = controller_dict[version][2]
    
    headers_serializer = HeadersSerializer()
    xml_serializer = wsgi.XMLDictSerializer(metadata, xmlns)
    json_serializer = wsgi.JSONDictSerializer()
    xml_deserializer = wsgi.XMLDeserializer(metadata)
    json_deserializer = wsgi.JSONDeserializer()

    body_serializers = {
        'application/xml': xml_serializer,
        'application/json': json_serializer,
    }

    body_deserializers = {
        'application/xml': xml_deserializer,
        'application/json': json_deserializer,
    }

    serializer = wsgi.ResponseSerializer(body_serializers, headers_serializer)
    deserializer = wsgi.RequestDeserializer(body_deserializers)

    return wsgi.Resource(controller, deserializer, serializer)
        

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