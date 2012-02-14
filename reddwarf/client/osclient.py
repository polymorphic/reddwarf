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
from novaclient import exceptions
from nova import flags
from nova import log as logging
import eventlet

FLAGS = flags.FLAGS

LOG = logging.getLogger('reddwarf.client.osclient')

class OSClient(object):
    '''
    classdocs
    '''


    def __init__(self, username, api_key, project_id, auth_url, region_name):
        '''
        Constructor
        '''
        password = api_key
        
        self.client = client.Client(username,password,project_id, auth_url, region_name=region_name)
        
    def create(self, hostname, image, flavor, key_name, security_groups):
        LOG.debug("OSClient - create()")
        return self.client.servers.create(hostname, image, flavor, key_name=key_name, security_groups=security_groups)
    
    def show(self, id):
        LOG.debug("OSClient - show()")
        #server = servers.Server()
        #server.id = id
        return self.client.servers.get(id)
    
    def assign_public_ip(self,id):
        LOG.debug("Assigning public IP to instance %s" % id)
        
        ip = None
        fl = self.client.floating_ips.list()
        for flip in fl:
            if flip.instance_id is None:
                # Choose one of the unassigned IPs
                ip = flip.ip
                #self.client.servers.add_floating_ip(id, flip.ip)
                break
        
        if ip is None:
            floating_ip = self.client.floating_ips.create(None)
            ip = floating_ip.ip
        
        LOG.debug("Found IP to Assign: %s" + str(ip) )
        
        success = False
        while(success is False):
            try:
                self.client.servers.add_floating_ip(id, ip)
                success = True
            except Exception:
                sucess = False
                LOG.debug('Sleeping')
                eventlet.sleep(1)
                LOG.debug('Awake')
                
            
        
        
        