# Copyright 2010 OpenStack LLC.
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

from nova import context
from nova import log as logging
from nova.api.openstack import wsgi
from nova import compute
from reddwarf import exception
from reddwarf.api import common
from reddwarf.db import api as dbapi
from reddwarf.guest import api as guest_api
from reddwarf.guest.db import models
from webob import exc


LOG = logging.getLogger('reddwarf.api.demo')
LOG.setLevel(logging.DEBUG)

class Controller(object):
    """ Demo E2E from API server to Agent instance """

    def __init__(self):
        self.guest_api = guest_api.API()
        self.compute_api = compute.API()
        super(Controller, self).__init__()


    def cast_smart_agent(self, req, instance_id):
        LOG.info("Call to demo asynchronous call to smart agent on instance %s", instance_id)
        ctxt = context.get_admin_context()
        try:
            result = self.guest_api.cast_smart_agent(ctxt, instance_id)
            return exc.HTTPAccepted()
        except Exception as err:
            LOG.error(err)
            raise exception.InstanceFault("Error triggering remote smart agent")


    def call_smart_agent(self, req, instance_id):
        """ Make sure the requested instance is running and remotely call smart agent """
        LOG.info("Call to demo synchronous call to smart agent on instance %s", instance_id)
        ctxt = context.get_admin_context()
        # localid = dbapi.localid_from_uuid(instance_id)
        # common.instance_available(ctxt, instance_id, localid, self.compute_api)
        try:
            result = self.guest_api.call_smart_agent(ctxt, instance_id)
            return {'Response': str(result)}
        except Exception as err:
            LOG.error(err)
            raise exception.InstanceFault("Error triggering remote smart agent")


def create_resource(version='1.0'):
    controller = {
        '1.0': Controller,
        }[version]()

    metadata = {
        "attributes": {
            'user': ['name', 'password']
        },
        }

    xmlns = {
        '1.0': common.XML_NS_V10,
        }[version]

    serializers = {
        'application/xml': wsgi.XMLDictSerializer(metadata=metadata,
            xmlns=xmlns),
        }

    response_serializer = wsgi.ResponseSerializer(body_serializers=serializers)

    return wsgi.Resource(controller, serializer=response_serializer)