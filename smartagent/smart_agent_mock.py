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

#!/usr/bin/env python
import pika
import json
import os
import time

# MQ server parameters
mq_host = '10.6.0.15'
exchange_name = 'nova'
rout_key = ''

# connect to RabbitMQ server and hook up on
# appropriate exchange, queue and routingkey
connection = pika.BlockingConnection(pika.ConnectionParameters(host=mq_host))
channel = connection.channel()
channel.exchange_declare(exchange=exchange_name, type='topic')
result = channel.queue_declare(exclusive=True)
queue_name = result.method.queue

# dynamically set routing key by instance hostname
rout_key = os.uname()[1]
channel.queue_bind(exchange=exchange_name,
    queue=queue_name,
    routing_key=rout_key)

# entry point of Smart Agent work
msg_count = 0
def do_agent_work(body):
    msg = json.loads(body)
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

# callback for MQ consumer
def on_request(ch, method, props, body):
    do_agent_work(body)
    ch.basic_ack(delivery_tag = method.delivery_tag)

channel.basic_qos(prefetch_count=1)
channel.basic_consume(on_request, queue=queue_name)

print "Awaiting requests from RedDwarf API server"
channel.start_consuming()