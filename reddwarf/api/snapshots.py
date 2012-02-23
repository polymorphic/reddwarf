#    Copyright 2012 OpenStack LLC
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

from webob import exc

from nova import compute
from nova import log as logging
from nova.api.openstack import wsgi
from nova.notifier import api as notifier
from nova import utils

from reddwarf import exception
from reddwarf.api import common
from reddwarf.api import deserializer
from reddwarf.api.views import snapshots
from reddwarf.guest import api as guest_api
from reddwarf.db import api as dbapi
from reddwarf.db import snapshot_state
from reddwarf.client import credential



LOG = logging.getLogger('reddwarf.api.snapshots')
LOG.setLevel(logging.DEBUG)

def publisher_id(host=None):
    return notifier.publisher_id("reddwarf-api", host)

class Controller(object):
    def __init__(self):
        self.guest_api = guest_api.API()
        self.compute_api = compute.API()
        self.view = snapshots.ViewBuilder()
        super(Controller, self).__init__()

    def show(self, req, id):
        """ Returns a requested snapshot """
        LOG.info("Get snapshot %s" % id)
        LOG.debug("%s - %s", req.environ, req.body)
        context = req.environ['nova.context']
        
        db_snapshot = dbapi.db_snapshot_get(context, id)
        snapshot = self.view.build_single(db_snapshot, req)

        return { 'snapshot' : snapshot }
    
    def index(self, req):
        """ Returns a list of Snapshots for the Instance """
        LOG.info("Get snapshots for snapshot id %s")
        LOG.debug("%s - %s", req.environ, req.body)
        context = req.environ['nova.context']

    def delete(self, req, id):
        """ Deletes a Snapshot """
        LOG.info("Delete snapshot with id %s", id)
        LOG.debug("%s - %s", req.environ, req.body)
        context = req.environ['nova.context']
        return exc.HTTPAccepted()

    def create(self, req, body):
        """ Creates a Snapshot """
        self._validate(body)
        instance_id = body['snapshot']['instanceId']
        name = body['snapshot']['name']
        LOG.info("Create Snapshot for instance %s", instance_id)
        LOG.debug("%s - %s", req.environ, req.body)
        
        context = req.environ['nova.context']

        # Generate UUID for Snapshot
        uuid = str(utils.gen_uuid())
        
        values = {
            'uuid' : uuid,
            'instance_uuid' : instance_id,
            'name' : name,
            'state' : snapshot_state.SnapshotState.INPROGRESS,
            'user_id' : context.user_id,
            'project_id' : context.project_id
            }
        
        # Add record to database
        db_snapshot = dbapi.db_snapshot_create(context, values)
        
        cred = credential.Credential('user','password','tenant')
        self.guest_api.create_snapshot(context, instance_id, uuid, cred)
        
        snapshot = self.view.build_single(db_snapshot, req)
        #TODO figure out how to send back a 201 along with body
        return { 'snapshot' : snapshot }

    def _validate(self, body):
        """Validate that the request has all the required parameters"""
        if not body:
            raise exception.BadRequest("The request contains an empty body")


def create_resource(version='1.0'):
    controller = {
        '1.0': Controller,
    }[version]()

    metadata = {
        "attributes": {
            "snapshot": ["id", "state", "availabilityZone", "createdTime", "instanceId",
                      "engine", "engineVersion"],
            "link": ["rel", "href"],
            },
    }

    xmlns = {
        '1.0': common.XML_NS_V10,
    }[version]

    serializers = {
        'application/xml': wsgi.XMLDictSerializer(metadata=metadata, xmlns=xmlns),
    }

    deserializers = {
        'application/xml': deserializer.InstanceXMLDeserializer(),
    }

    response_serializer = wsgi.ResponseSerializer(body_serializers=serializers)
    request_deserializer = wsgi.RequestDeserializer(deserializers)
    return wsgi.Resource(controller, deserializer=request_deserializer, serializer=response_serializer)
