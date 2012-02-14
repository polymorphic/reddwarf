# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
This is a standalone application to connect to RabbitMQ server and consume
the RPC messages sent from API Server through rpc.cast or rpc.call.
It mocks SmartAgent and depends on pika AMQP library but has no dependency
on any RedDwarf code.
"""

#!/usr/bin/env python
import json
import os
import time

import pika

from check_mysql_status import MySqlChecker
import command_handler

# State codes for Reddwarf API
NOSTATE = 0x00
RUNNING = 0x01
BLOCKED = 0x02
PAUSED = 0x03
SHUTDOWN = 0x04
SHUTOFF = 0x05
CRASHED = 0x06
SUSPENDED = 0x07
FAILED = 0x08
BUILDING = 0x09


class SmartAgent:
    
    """This class provides an agent able to communicate with a RedDwarf API
       server and take action on a particular RedDwarf instance based on the
       contents of the messages received."""
    
    def __init__ (self):     
        """Constructor.  Initializes the MQ server connection."""
        
        self.msg_count = 0
        self.mq_host = '15.185.163.167'
        self.exchange_name = 'nova'
        
        # Dynamically set routing key using the instance hostname.
        self.routing_key = os.uname()[1]
        
        # Set MQ server values.
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=self.mq_host))
        self.channel = self.connection.channel()
        self.exchange = self.channel.exchange_declare(
            exchange=self.exchange_name, type='topic')
        self.result = self.channel.queue_declare(exclusive=True)
        self.queue_name = self.result.method.queue
        self.queue_bind = self.channel.queue_bind(
            exchange=self.exchange_name, queue=self.queue_name, 
            routing_key=self.routing_key)         

    def start_consuming(self):
        """Sets the properties for message consumption and then establishes
           a connection with the MQ server.
           
           Arguments:   self
           Return type: void"""
           
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(self.on_request, queue=self.queue_name)
        
        # Consumer loop to read incoming messages.
        print "<Awaiting requests from RedDwarf API server>\n"
        reader = self.channel
        reader.start_consuming()
   
    def do_agent_work(self, msg):
        """Performs actual agent work.  Called by on_request() whenever
           a message is received, and calls the appropriate function based
           on the contents of the method key in the message.
           
           Arguments:   self 
                        msg -- A dictionary representation of a JSON object
           Return type: A dictionary of {result of method execution, 
                        failure code (default for each is None)}"""
                                    
        self.msg_count += 1
        result = None
        failure = None
        agent_username = 'root'
        
        # Make sure the method key is part of the JSON - if not, it's
        # invalid.
        # TODO: Return appropriate result/failure values (currently 
        # None/None)
        try:
            method = msg['method']
        except KeyError:
            print "KeyError exception - unexpected message format:"
            print msg
            return { 'result': result, 'failure': failure }
        
        # Do work based on passed method value:
        print ("     [-] Method requested", str(self.msg_count), 
               ": ", msg['method'])
        
        if method == 'reset_password':
            handler = command_handler.MysqlCommandHandler()
            result = handler.reset_user_password(
                agent_username, msg['args']['password'])
        elif method == 'check_mysql_status':
            checker = MySqlChecker()
            result = checker.check_if_running(sleep_time_seconds=3, 
                                              number_of_checks=5)
            if result:
                result = RUNNING
            else:
                result = NOSTATE
        elif method == 'create_user':
            pass
        elif method == 'list_users':
            pass
        elif method == 'delete_user':
            pass
        elif method == 'create_database':
            pass
        elif method == 'list_databases':
            pass
        elif method == 'delete_database':
            pass
        elif method == 'enable_root':
            pass
        elif method == 'disable_root':
            pass
        elif method == 'is_root_enabled':
            pass
        elif method == 'prepare':
            pass
        elif method == 'update_status':
            pass
        else:
            print "Agent triggered to collect system info ..."
            hostname = os.uname()[1]
            unumber = os.getuid()
            pnumber = os.getpid()
            where = os.getcwd()
            what = os.uname()
            now = time.time()
            means = time.ctime(now)
            print "   Hostname: ", hostname
            print "   User ID: ", unumber
            print "   Process ID: ", pnumber
            print "   Current Directory: ", where
            print "   System information: ", what
            print "   Time is now: ", means
            
        return { 'result': result, 'failure': failure }

    def send_response(self, message, props, response_id):
        """Sends response back to the exclusive direct exchange for rpc.call -
           the message should be a dictionary.
           
           Arguments:   self
                        message -- Dictionary containing the response to API
                                   server
                        props   -- Properties for the connection object
                        response_id -- String containing the exchange to use
                                       for the response
           Return type: None"""
           
        self.channel.basic_publish(exchange=response_id,
                                   routing_key=response_id,
                                   properties=pika.BasicProperties(
                                       correlation_id = props.correlation_id),
                                   body=str(message))

    def end_response(self, props, response_id):
        """Send end response signal back when there are no more responses to 
           send so the rpc.call client on API Server can disconnect the channel
           (required by the RedDwarf RPC protocol).
           
           Arguments:   self
                        props   -- Properties for the connection object
                        response_id -- String containing the exchange to use
                                       for the response
           Return type: None"""
           
        # The end response signal is defined by the RPC protocol.
        end_message = {'result': None, 'failure': None}
        self.channel.basic_publish(exchange=response_id,
                                   routing_key=response_id,
                                   properties=pika.BasicProperties(
                                       correlation_id = props.correlation_id),
                                   body=str(end_message))

    def on_request(self, channel, method, props, body):
        """ Callback for MQ message consumer.  Called whenever a message is
            consumed.
            
            Arguments:   self
                         channel -- The connection object for the MQ server
                         method  -- Delivery properties for the channel object
                         props   -- Properties for the connection object
                         body    -- String containing the actual message
            Return type: None"""
            
        print " [x] Received %r" % (body,)
        msg = None
        
        # Make sure that we properly handle malformed JSON strings.
        try:
            msg = json.loads(body)
        except ValueError:
            channel.basic_ack(delivery_tag = method.delivery_tag)
            print "ValueError exception - improperly formatted JSON:"
            print body
        else:
            channel.basic_ack(delivery_tag = method.delivery_tag)
            response = self.do_agent_work(msg)
            
            # If the '_msg_id' key is present, we need a response to the 
            # rpc.call.
            if '_msg_id' in msg:
                print "     [-] Responding to rpc.call: ", response, "\n"
                
                # The '_msg_id' key is used to identify the MQ channel for
                # responding (enables mapping to exchange & routing keys).
                response_id = msg['_msg_id']
                self.send_response(response, props, response_id)
                self.end_response(props, response_id)


def main():
    """Activates the smart agent by instantiating an instance of SmartAgent
       and then calling its start_consuming() method."""
        
    agent = SmartAgent()
    agent.start_consuming()
    
if __name__ == '__main__':
    main()
