#    Copyright 2011 OpenStack LLC
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

'''
Created on Feb 1, 2012

@author: vipul
'''
from novaclient.v1_1 import client
from novaclient.v1_1 import servers
from nova import flags
from nova import log as logging

FLAGS = flags.FLAGS

LOG = logging.getLogger('reddwarf.client.osclient')

class OSClient(object):
    '''
    classdocs
    '''


    def __init__(self, username, api_key, project_id, auth_url):
        '''
        Constructor
        '''
        password = api_key
        
        self.client = client.Client(username,password,project_id, auth_url)
        
    def create(self, name, image, flavor):
        LOG.debug("OSClient - create()")
        return self.client.servers.create(name, image, flavor)
    
    def show(self, id):
        LOG.debug("OSClient - show()")
        #server = servers.Server()
        #server.id = id
        return self.client.servers.get(id)