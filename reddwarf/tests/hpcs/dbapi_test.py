#    Copyright 2012 Hewlett-Packard Development Company, L.P.
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
import unittest
import json
import httplib2

API_URL = "http://15.185.163.25:8775/v1.0/dbaasapi/"
AUTH_TOKEN = "abc:123"
AUTH_HEADER = {'X-Auth-Token': AUTH_TOKEN, 'content-type': 'application/json', 'Accept': 'application/json'}
created_instance = False

logging.basicConfig()

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

class DBFunctionalTests(unittest.TestCase):
    
    def test_instance_api(self):
        """Comprehensive instance api test using an instance lifecycle."""
        
        """1) Test creating a db instance."""
        LOG.debug("* Creating db instance")
        body = r"""
        {"instance": {
            "name": "dbapi_test",
            "flavorRef": "102",
            "port": "3306",
            "dbtype": {
                "name": "mysql",
                "version": "5.1.2"
            },
            "databases": [
                {
                    "name": "testdb",
                    "character_set": "utf8",
                    "collate": "utf8_general_ci"
                },
                {
                    "name": "abcdefg"
                }
            ],
            "volume":
                {
                    "size": "2"
                }
            }
        }"""
        
        req = httplib2.Http(".cache")
        resp, content = req.request(API_URL + "instances", "POST", body, AUTH_HEADER)
        content = json.loads(content)
        LOG.debug(resp)
        LOG.debug(content)
        self.instance_id = content['instance']['id']
        LOG.debug("Instance ID: %s" % self.instance_id)
        

        """Assert 1) that the request was accepted and 2) that the response
           is in the expected format."""
        self.assertEqual(resp.status, 200)
        self.assertTrue(content.has_key('instance'))
        #self.instance_id = "e48fe6b6-77d5-4619-9ed7-8f39231bded7"
       
    
        """2) Test listing all db instances."""
        LOG.debug("* Listing all db instances")
        req = httplib2.Http(".cache")
        resp, content = req.request(API_URL + "instances", "GET", "", AUTH_HEADER)
        content = json.loads(content)
        
        print resp
        print content
        """Assert 1) that the request was accepted and 2) that the response is
           in the expected format (e.g. a JSON object beginning with an
           'instances' key)."""
        self.assertEqual(resp.status, 200)
        self.assertTrue(content.has_key('instances'))
    
    
        """3) Test getting a specific db instance."""
        LOG.debug("* Getting instance %s" % self.instance_id)
        req = httplib2.Http(".cache")
        resp, content = req.request(API_URL + "instances/" + self.instance_id, "GET", "", AUTH_HEADER)
        content = json.loads(content)
        
        print resp
        print content
        """Assert 1) that the request was accepted and 2) that the returned 
           instance is the same as the accepted instance."""
        self.assertEqual(resp.status, 200)
        self.assertEqual(self.instance_id, content['instance']['id'])
    
    
#        """4) Test resetting the password on a db instance."""
#        LOG.debug("* Resetting password on instance %s" % self.instance_id)
#        req = httplib2.Http(".cache")
#        resp, content = req.request(API_URL + "instances/" + self.instance_id + "/resetpassword", "POST", "", AUTH_HEADER)
#        #content = json.loads(content)
#        
#        print resp
#        print content
#        """Assert 1) that the request was accepted."""
#        self.assertEqual(resp.status, 202)
#        #self.assertEqual(self.instance_id, content['instance']['id'])   
    
    
#        """5) Test restarting a db instance."""
#        LOG.debug("* Restarting instance %s" % self.instance_id)
#        LOG.debug("  - Sending %s command: %s" % ("POST", API_URL + "instances/" + self.instance_id + "/restart"))
#        req = httplib2.Http(".cache")
#        resp, content = req.request(API_URL + "instances/" + self.instance_id + "/restart", "POST", "", AUTH_HEADER)
#        #content = json.loads(content)
#        
#        print resp
#        print content
#        """Assert 1) that the request was accepted."""
#        self.assertEqual(resp.status, 202)
#        #self.assertEqual(self.instance_id, content['instance']['id'])
    
    
        """6) Test deleting a db instance."""
        LOG.debug("* Deleting instance %s" % self.instance_id)
        req = httplib2.Http(".cache")
        resp, content = req.request(API_URL + "instances/" + self.instance_id, "DELETE", "", AUTH_HEADER)
        
        print resp
        print content
        """Assert 1) that the request was accepted and 2) that the instance no
           longer exists."""
        self.assertEqual(resp.status, 202)
        
        resp, content = req.request(API_URL + "instances", "GET", "", AUTH_HEADER)
        content = json.loads(content)
        
        for each in content['instances']:
            self.assertFalse(each['id'] == self.instance_id)
    
    def test_dbsnapshot_list(self):
        """Test listing all db snapshots."""
        pass
    
    def test_dbsnapshot_create(self):
        """Test creating a db snapshot."""
        pass
    
    def test_dbsnapshot_get(self):
        """Test getting a specific db snapshot."""
        pass
    
    def test_dbsnapshot_delete(self):
        """Test deleting a db snapshot."""
        pass

#    def test_instances_create(self):
#        """Test to create an instance on nova"""
#        print("Testing create instance call")
#        
#        body = r"""
#        {"instance": {
#            "name": "dbapi_test",
#            "flavorRef": "102",
#            "port": "3306",
#            "dbtype": {
#                "name": "mysql",
#                "version": "5.1.2"
#            },
#            "databases": [
#                {
#                    "name": "testdb",
#                    "character_set": "utf8",
#                    "collate": "utf8_general_ci"
#                },
#                {
#                    "name": "abcdefg"
#                }
#            ],
#            "volume":
#                {
#                    "size": "2"
#                }
#            }
#        }"""
#        
#        req = httplib2.HTTPSConnectionWithTimeout(COMPUTE_URL)
#        print COMPUTE_PATH + "instances"
#        print body
#        req.request("POST", COMPUTE_PATH + "instances", body, self.tokenHeader())
#        response = req.getresponse()
#        responseContent = response.read()
#        
#        print (responseContent)
#        print self.tokenHeader()
#        self.assertEqual(response.status, 200)
        
    def tearDown(self):
        pass