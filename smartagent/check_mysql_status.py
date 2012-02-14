#!/usr/bin/python

# Copyright 2010 OpenStack, LLC
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

__author__ = 'dragosmanolescu'
__email__ = 'dragosm@hp.com'
__python_version__ = '2.7.2'

import sys
import time
from smartagent_persistence import DatabaseManager
import logging
logging.basicConfig()

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

class MySqlChecker:
    """
    Make a given number of attempts to determine whether a MySQL instance is
    up an running on the given host
    The credentials for connecting to the database are pulled from an option
    file, which is provided as an argument
    """
    def __init__(self, host_name='localhost',
                 database_name='information_schema', config_file='~/.my.cnf'):
        self.database_name = database_name
        self.host_name = host_name
        self.config_file = config_file
        # singleton
        self.persistence_agent = DatabaseManager(host_name=host_name
            , database_name=database_name, config_file=config_file)
        self.persistence_agent.open_connection()

    def is_running(self):
        """
        Performs one check by issuing the stat command.
        Returns True if stat returns a non-empty string, False otherwise
        """
        result = False
        try:
            result = self.persistence_agent.status()
        except:
            pass # swallow exception
            LOG.error('Exception while trying to connect to database: %s',
                str(sys.exc_info()[0]))
        return result

    def check_if_running(self, sleep_time_seconds=60, number_of_checks=10):
        """
        Performs number_of_checks, waiting sleep_time_seconds between them.
        Upon receiving True from isRunning it returns True; if that hasn't
        happened after the given number of checks returns False
        """
        iteration = 0
        try:
            while iteration < number_of_checks:
                LOG.debug('Checking iteration %d' % iteration)
                if self.is_running():
                    return True
                else:
                    time.sleep(sleep_time_seconds)
                    iteration = iteration + 1
            return False
        except:
            LOG.error('Exception while iterating, aborting: %s',
                sys.exc_info()[0])
            raise


def main():
    checker = MySqlChecker()
    if checker.check_if_running(5, 7):
        # send phone home message
        print 'MySQL is running'
    else:
        print 'MySQL is not running'
        # send message signaling that MySQL is not running
    sys.exit(0)

if __name__ == '__main__':
    main()
