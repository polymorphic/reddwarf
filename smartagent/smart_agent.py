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

import os
import logging
import time

from smartagent_messaging import MessagingService
from check_mysql_status import MySqlChecker
import command_handler

logging.basicConfig()

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

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

    def __init__(self):
        self.msg_count = 0
        self.messaging = MessagingService()
        self.messaging.callback = self.process_message
        self.agent_username = 'root'

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

    def restart_database_instance(self, msg):
        LOG.debug('Functionality not implemented')
        result = None
        return result

    def reset_password(self, msg):
        handler = command_handler.MysqlCommandHandler() # TODO extract into instance variable
        result = handler.reset_user_password(
            self.agent_username, msg['args']['password'])
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
        checker = MySqlChecker()  # TODO extract into instance variable
        result = checker.check_if_running(sleep_time_seconds=3,
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
        response = {'result' : None, 'failure' : None}
        return response

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

        # Make sure the method key is part of the JSON - if not, it's
        # invalid.
        # TODO: Return appropriate result/failure values (currently 
        # None/None)
        try:
            method = msg['method']
        except KeyError:
            LOG.error('Message missing "method" element: %s', msg)
            return {'result': result, 'failure': failure}
        LOG.debug ('Dispatching %s (%d)', method, self.msg_count)
        #  internal API
        if method == 'create_instance':
            result = self.create_database_instance(msg)
        elif method == 'delete_instance':
            result = self.delete_database_instance(msg)
        elif method == 'restart_instance':
            result = self.restart_database_instance(msg)
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
        else:
            result = self.get_system_info()
        return {'result': result, 'failure': failure}


def main():
    """Activates the smart agent by instantiating an instance of SmartAgent
       and then calling its start_consuming() method."""

    agent = SmartAgent()
    agent.start()

if __name__ == '__main__':
    main()
