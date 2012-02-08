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

# MQ server parameters
mq_host = '15.185.163.167'
exchange_name = 'nova'
rout_key = ''

# connect to RabbitMQ server and hook up on appropriate exchange,
# queue and routingkey for receiving request message
connection = pika.BlockingConnection(pika.ConnectionParameters(host=mq_host))
channel = connection.channel()
channel.exchange_declare(exchange=exchange_name, type='topic')
result = channel.queue_declare(exclusive=True)
queue_name = result.method.queue
# dynamically set routing key by instance hostname
rout_key = os.uname()[1]
channel.queue_bind(exchange=exchange_name, queue=queue_name, routing_key=rout_key)

# entry point of Smart Agent work
msg_count = 0
def do_agent_work(msg):
    global msg_count
    msg_count += 1
    print "\n>>> Method requested ", str(msg_count), ": ", msg['method']
    print "Agent triggered to collect system info ..."
    get_sys_info()

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

# callback for MQ consumer
def on_request(ch, method, props, body):
    print " [x] Received %r" % (body,)
    msg = json.loads(body)
    do_agent_work(msg)
    ch.basic_ack(delivery_tag = method.delivery_tag)

    # send response back if response is requested by
    # presenting '_msg_id' key in the request json
    if '_msg_id' in msg:
        # set response in dictionary
        reply = 'success'
        failure = None
        response = {'result': reply, 'failure': failure}
        # The '_msg_id' is used to identify the response MQ channel (exchange & routing key)
        response_id = msg['_msg_id']
        send_response(response, ch, props, response_id)
        end_response(ch, props, response_id)

channel.basic_qos(prefetch_count=1)
channel.basic_consume(on_request, queue=queue_name)

print "Awaiting requests from RedDwarf API server"
channel.start_consuming()
