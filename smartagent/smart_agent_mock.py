#!/usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010 OpenStack LLC.
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
It mocks SmartAgent and depends on pika AMQP library and has no dependency
on any RedDwarf code.
"""

#!/usr/bin/env python
import pika
import json
import os
import time
import check_mysql_status
import sys

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

# MQ server parameters
mq_host = '15.185.163.167'
exchange_name = 'nova'

# dynamically set routing key by instance hostname
routing_key = os.uname()[1]

# connect to RabbitMQ server and hook up on appropriate exchange,
# queue and routingkey for receiving request message
connection = pika.BlockingConnection(pika.ConnectionParameters(host=mq_host))
channel = connection.channel()
channel.exchange_declare(exchange=exchange_name, type='topic')
result = channel.queue_declare(exclusive=True)
queue_name = result.method.queue
channel.queue_bind(exchange=exchange_name, queue=queue_name, routing_key=routing_key)

# entry point of Smart Agent work
msg_count = 0
def do_agent_work(msg):
    
    result = None
    failure = None
    agent_username = 'root'
    
    try:
        global msg_count
        msg_count += 1
        print "     [x]  Method requested ", str(msg_count), ": ", msg['method']
        method = msg['method']
        if msg['method']=='reset_password':
            handler = command_handler.MysqlCommandHandler()
            result = handler.reset_user_password(agent_username, msg['args']['password'])
            
        elif method == 'check_mysql_status':
            checker = check_mysql_status.MySqlChecker()
            result = checker.check_if_running(sleep_time_seconds=3, number_of_checks=5)
            if result:
                result = RUNNNING
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
            get_sys_info()
    except KeyError:
        print "KeyError exception - received message in an unexpected format:"
        print msg
        
    return { 'result': result, 'failure': failure }
    
    

# sample agent work to collect system info
def get_sys_info():
    hostname = os.uname()[1]
    unumber = os.getuid()
    pnumber = os.getpid()
    where = os.getcwd()
    what = os.uname()
    now = time.time()
    means = time.ctime(now)
    print "   Hostname: ",hostname
    print "   User ID: ",unumber
    print "   Process ID: ",pnumber
    print "   Current Directory: ",where
    print "   System information: ",what
    print "   Time is now: ", means

# send response back to the exclusive direct exchange for rpc.call
# the message should be a dictionary
def send_response(message, ch, props, response_id):
    ch.basic_publish(exchange=response_id,
                     routing_key=response_id,
                     properties=pika.BasicProperties(correlation_id = props.correlation_id),
                     body=str(message))

# send response ending signal back when no more responses to send
# so the rpc.call client on API Server can disconnect the channel
# this is required by the RedDwarf RPC protocol
def end_response(ch, props, response_id):
    # ending message is defined by the RPC protocol
    end_message = {'result': None, 'failure': None}
    ch.basic_publish(exchange=response_id,
                     routing_key=response_id,
                     properties=pika.BasicProperties(correlation_id = props.correlation_id),
                     body=str(end_message))

# Callback for MQ consumer.  Catches ValueError exceptions to avoid breaking 
# due to malformed JSON.
def on_request(ch, method, props, body):
    # TODO debug output will be redirected once logging is ready
    # print " [x] Received %r" % (body,)
    msg = None
    try:
        msg = json.loads(body)
    except ValueError:
        ch.basic_ack(delivery_tag = method.delivery_tag)
        print "ValueError exception - received a message containing improperly formatted JSON:"
        print body
    else:
        ch.basic_ack(delivery_tag = method.delivery_tag)
        response = do_agent_work(msg)
        
        # send response back if response is requested by
        # presenting '_msg_id' key in the request json
        if '_msg_id' in msg:
            print "     [x] Got rpc.call. Sending response: ", response, "\n"
            
            # The '_msg_id' is used to identify the response MQ channel (exchange & routing key)
            response_id = msg['_msg_id']
            send_response(response, ch, props, response_id)
            end_response(ch, props, response_id)

channel.basic_qos(prefetch_count=1)
channel.basic_consume(on_request, queue=queue_name)

print "Awaiting requests from RedDwarf API server\n"

# Consumer loop to read incoming messages.
channel.start_consuming()

