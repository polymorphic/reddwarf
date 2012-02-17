#!/usr/bin/env python
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

from subprocess import call
import json

import os
import logging
import time

from smartagent_messaging import MessagingService
from check_mysql_status import MySqlChecker
from command_handler import MysqlCommandHandler

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)8s %(message)s',
                    filemode='a')
LOG = logging.getLogger()
fh = logging.FileHandler('./smartagent.log')
fh.setLevel(logging.DEBUG)
LOG.addHandler(fh)

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

    def __init__(self, msg_service):
        self.msg_count = 0
        self.messaging = msg_service
        self.messaging.callback = self.process_message
        self.agent_username = 'root'
        self.checker = MySqlChecker()  # TODO extract into instance variable

    def start(self):
        self.messaging.start_consuming()

    def create_database_instance(self, msg):
        LOG.debug('Functionality not implemented')
        result = None
        return result

    def delete_database_instance(self, msg):
        LOG.debug('Functionality not implemented')
        result = None
        return result

    def create_database(self, msg):
        handler = MysqlCommandHandler()
        result = handler.create_database(msg['args']['database'])
        return result

    def restart_database(self, msg):
        result = call("sudo service mysql restart", shell=True)
        return result

    def restart_database_instance(self, msg):
        LOG.debug('Functionality not implemented')
        result = None
        return result

    def reset_password(self, msg):
        handler = MysqlCommandHandler() # TODO extract into instance variable
        result = handler.reset_user_password(
            self.agent_username, msg['args']['password'])
        return result

    def create_user(self, msg):
        handler = command_handler.MysqlCommandHandler()
        result = handler.create_user(
            msg['args']['username'], 
            msg['args']['hostname'],
            msg['args']['password'])
        return result

    def delete_user(self, msg):
        handler = command_handler.MysqlCommandHandler()
        result = handler.delete_user(msg['args']['username'])
        return result

    def take_database_snapshot(self, msg):
        LOG.debug('Functionality not implemented')
        result = None
        return result

    def list_database_snapshots(self, msg):
        LOG.debug('Functionality not implemented')
        result = None
        return result

    def delete_database_snapshot(self, msg):
        LOG.debug('Functionality not implemented')
        result = None
        return result

    def check_status(self):
        result = self.checker.check_if_running(sleep_time_seconds=3,
            number_of_checks=5)
        if result:
            result = RUNNING  # TODO remove dependencies from VM state codes
        else:
            result = NOSTATE
        return result

    def get_system_info(self):
        LOG.debug('System info')
        hostname = os.uname()[1]
        unumber = os.getuid()
        pnumber = os.getpid()
        where = os.getcwd()
        what = os.uname()
        now = time.time()
        means = time.ctime(now)
        # TODO: assemble into string and inject in response
        LOG.debug("Hostname: %s", hostname)
        LOG.debug("User ID: %s", unumber)
        LOG.debug("Process ID: %s", pnumber)
        LOG.debug("Current Directory: %s", where)
        LOG.debug("System information: %s", what)
        LOG.debug("Time is now: %s", means)
        result = None
        return result

    def process_message(self, msg):
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

        # will use this for reset agent password
        # agent_username = 'os_admin'
        
        # Make sure the method key is part of the JSON - if not, it's
        # invalid.
        # TODO: Return appropriate result/failure values (currently 
        # None/None)
        try:
            method = msg['method']
        except KeyError:
            LOG.error('Message missing "method" element: %s', msg)
            return {'result': result, 'failure': 'missing_method'}
        LOG.debug ('Dispatching %s (%d)', method, self.msg_count)
        #  internal API
        if method == 'create_instance':
            result = self.create_database_instance(msg)
        elif method == 'delete_instance':
            result = self.delete_database_instance(msg)
        elif method == 'restart_instance':
            result = self.restart_database_instance(msg)
        elif method == 'restart_database':
            result = self.restart_database(msg)
        elif method == 'create_user':
            result = self.create_user(msg)
        elif method == 'delete_user':
            result = self.delete_user(msg)
        elif method == 'create_database':
            result = self.create_database(msg)
        elif method == 'reset_password':
            result = self.reset_password(msg)
        elif method == 'take_snapshot':
            result = self.take_database_snapshot(msg)
        elif method == 'list_snapshots':
            result = self.list_database_snapshots(msg)
        elif method == 'delete_snapshot':
            result = self.delete_database_snapshot(msg)
        elif method == 'check_mysql_status':
            result = self.check_status()
        elif method == 'check_system_status':
            result = self.get_system_info()
        else:
            failure = 'unsupported_method'
        return {'result': result, 'failure': failure}


def main():
    """Activates the smart agent by instantiating an instance of SmartAgent
       and then calling its start_consuming() method."""

    # Start a RabbitMQ MessagingService instance
    msg_service = MessagingService()
    
    agent = SmartAgent(msg_service)
    agent.start()

if __name__ == '__main__':
    main()
