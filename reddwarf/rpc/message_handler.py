# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2011 Justin Santa Barbara
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

"""Proxy classes to handle messages coming from remote agent in a passive mode."""

from nova import flags
from nova import log as logging
from nova.rpc import impl_kombu
from reddwarf.guest import api as guest_api

FLAGS = flags.FLAGS
LOG = logging.getLogger('nova.guest.api')
flags.DEFINE_string('phone_home_exchange', 'phonehome',
    'default topic name for phone home messaging')


class MessageHandlerService():
    """A background service to listen on MQ and handle messages pushed from remote agents.
       It will be started on an independent thread living through the API Server lifetime."""
    def __init__(self):
        self._listener = None
        self._msg_handler = guest_api.PhoneHomeMessageHandler()

    def start(self):
        """Setup connection to MQ with one single consumer to handle
           phone home messages from all remote instances"""
        LOG.debug("Starting Message Handler Service...")
        self._listener = impl_kombu.listen(FLAGS.phone_home_exchange, self._msg_handler)

    def stop(self):
        """Close consumer to MQ"""
        self._listener.done()
        LOG.debug("Message Handler Service is stopped.")
