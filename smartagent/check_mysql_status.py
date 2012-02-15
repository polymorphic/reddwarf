#!/usr/bin/python

# Copyright 2012 OpenStack, LLC
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
import os.path
import errno
import socket
import re
import logging
logging.basicConfig()

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


class MySqlChecker:
    """
    Make a given number of attempts to determine whether a MySQL instance is
    up an running on the given host
    """
    def __init__(self,
                 host_name='127.0.0.1',
                 port_number=3306,
                 pid_file_path='/var/lib/mysql'):
        self.host_name = host_name
        self.port_number = port_number
        self.pid_file_path = pid_file_path

    def is_running(self):
        """
        Checks if mysqld is running:
        - First look for the pid file (distribution-dependent; default value for ubuntu)
        - Next kill -0 to check if the process is running (same as in the mysql.server script)
        - Finally open the socket and look for the version number in the protocol handshake string
        """
        pid_file_name = os.path.join(self.pid_file_path, os.uname()[1]) \
            + '.pid'
        LOG.debug('Checking pid file: %s', pid_file_name)
        if not os.path.isfile(pid_file_name):
            return False
        with open(pid_file_name, 'r') as pid_file:  # read permissions required!
            pid_string = pid_file.read()
            LOG.debug('pid file read: %s', pid_string)
        try:
            os.kill(int(pid_string), 0)
        except OSError as err:
            if err.errno == errno.ESRCH:
                LOG.debug('os.kill: no such process %s', pid_string)
                return False
            elif err.errno == errno.EPERM:
                LOG.debug('os.kill: operation not permitted on process %s',
                    pid_string)
                return False
            else:
                LOG.error('os.kill: other error (%s)', str(sys.exc_info()[0]))
        else:
            LOG.debug('os.kill: process %s is running', pid_string)
            try:
                mysql_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                mysql_socket.connect((self.host_name, self.port_number))
                response = mysql_socket.recv(4096)
                LOG.debug('mysqld protocol response: %s', response)
            except:
                LOG.error('Error connecting to mysqld on %s:%d',
                    self.host_name, self.port_number)
            else:
                mysql_socket.close()
                LOG.debug('Looking for MySQL protocol version 5.X.X')
                # TODO: MySQL protocol version-dependent
                regex = re.compile('5.[0-9]+.[0-9]+')
                matches = regex.findall(response)  # http://www.pythonregex.com/
                return len(matches) > 0
            return False

    def check_if_running(self, sleep_time_seconds=5, number_of_checks=10):
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
    platform = os.uname()[3].lower()
    if platform.find('ubuntu') > -1:
        print 'Running on Linux'
        checker = MySqlChecker()
        # using defaults
    elif platform.find('darwin') > -1:
        print 'Running on OS X'
        checker = MySqlChecker(pid_file_path='/usr/local/var/mysql')
    else:
        print 'Unsupported platform?'
        sys.exit(-1)

    if checker.check_if_running(5, 7):
        # send phone home message
        print 'MySQL is running'
    else:
        print 'MySQL is not running'
        # send message signaling that MySQL is not running
    sys.exit(0)

if __name__ == '__main__':
    main()
