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

import sys
import os
import time
import atexit
import ConfigParser
import logging
from signal import SIGTERM 
from subprocess import call
from result_state import ResultState
from smartagent_messaging import MessagingService
from check_mysql_status import MySqlChecker
from command_handler import MysqlCommandHandler

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)8s %(message)s',
                    filemode='a')

AGENT_HOME = '/home/nova'
AGENT_CONFIG = '/home/nova/agent.config'
LOG = logging.getLogger(__name__)

FH = logging.FileHandler(os.path.join(AGENT_HOME,
    'logs',
    'smartagent.log'))
FH.setLevel(logging.DEBUG)
LOG.addHandler(FH)

class SmartAgent:
    """This class provides an agent able to communicate with a RedDwarf API
    server and take action on a particular RedDwarf instance based on the
    contents of the messages received."""

    def __init__(self):
        """ Constructor method """
        # pylint thought too many arguments. But should keep around.
        self.pidfile = os.path.join(AGENT_HOME,
            'lock',
            'smartagent.pid')
        self.stdin = '/dev/null' 
        self.stdout = '/dev/null'
        self.stderr = '/dev/null'
        self.msg_count = 0
        self.agent_username = 'os_admin'
        self.checker = MySqlChecker()
        self.handler = MysqlCommandHandler()
        # get RabbitMQ config
        self.messaging = None
        mq_conf = load_config("messaging")
        if not mq_conf:
            self.messaging = MessagingService()    # using default MQ host
        else:
            self.messaging = MessagingService(host_address=mq_conf['rabbit_host'])
        # get snapshot config if any
        self.snapshot_conf = load_config("snapshot")
        self.messaging.callback = self.process_message

    def load_config(self, section):
        result = {}
        config = ConfigParser.ConfigParser()
        config.read(AGENT_CONFIG)
        try:
            options = config.options(section)
        except:
            return None
        for option in options:
            try:
                result[option] = config.get(section, option)
            except:
                result[option] = None
        return result

    def daemonize(self):
        """ This method is for the purpose of the smart agent
        to run as a daemon and have better control over its running """

        # fork the daemon 
        try:
            pid = os.fork()
            if pid > 0:
                LOG.debug("Exiting first parent")
                sys.exit(os.EX_OK)
        except OSError, err:
            sys.stderr.write("fork #1 failed: %d (%s)\n" %
            (err.errno, err.strerror))
            sys.exit(os.EX_OSERR)
       
        # decouple from parent environment
        os.chdir(AGENT_HOME)
        os.setsid()
        os.umask(0)
       
        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                LOG.debug("Exiting second parent")
                sys.exit(os.EX_OK)  # should this be _exit() ?
        except OSError, err:
            sys.stderr.write("fork #2 failed: %d (%s)\n" %
            (err.errno, err.strerror))
            sys.exit(os.EX_OSERR)
       
        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        std_i = file(self.stdin, 'r')
        std_o = file(self.stdout, 'a+')
        std_e = file(self.stderr, 'a+', 0)
        os.dup2(std_i.fileno(), sys.stdin.fileno())
        os.dup2(std_o.fileno(), sys.stdout.fileno())
        os.dup2(std_e.fileno(), sys.stderr.fileno())
       
        # write pidfile
        atexit.register(self.remove_pid_file)
        pid = str(os.getpid())
        LOG.debug("pid: %s", pid)
        with open(self.pidfile,'w+') as f:
            f.write("%s\n" % pid)

    def remove_pid_file(self):
        """Delete the PID file when done"""
        os.remove(self.pidfile)

    def start(self):
        """ Start the smart agent, daemon process """

        # Check for a pidfile to see if the daemon already runs
        LOG.debug('Checking for %s', self.pidfile)
        if os.path.isfile(self.pidfile):
            # TODO: also check that the process is running
            sys.stderr.write("Daemon already running?\n" % self.pidfile)
            sys.exit(os.EX_USAGE)

        # Start the daemon
        self.daemonize()
        self.run()

    def stop(self):
        """ Stop the daemon """
        LOG.debug('Checking for %s', self.pidfile)
        if not os.path.isfile(self.pidfile):
            sys.stderr.write("PID file not found: %s\n" % self.pidfile)
            sys.exit(os.EX_OK)  # TODO: do not exit so can restart a stopped agent
        # Get the pid from the pidfile
        with open(self.pidfile,'r') as f:
            pid_string = f.read().strip()
        try:
            pid = int(pid_string)
        except ValueError:
            pid = None
        if not pid:
            sys.stderr.write("Can't parse PID form pidfile: %s\n" % self.pidfile)
            sys.exit(os.EX_OSFILE)

        # Try killing the daemon process       
        try:
            while 1:  # TODO: prevent infinite loop
                os.kill(pid, SIGTERM)
                time.sleep(0.1)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
                else:
                    print str(err)
                    sys.exit(os.EX_UNAVAILABLE)

    def restart(self):
        """ Restart the daemon """
        self.stop()
        self.start()

    def run(self):
        """ Run the smart agent """
        if not self.snapshot_conf:
            # initial check for DB status and phone home to API Server
            state = self.check_status()
            hostname = os.uname()[1]
            message = {"method": "update_instance_state",
                       "args": {'hostname': hostname, 'state': str(state)}}
            try:
                self.messaging.phone_home(message)
                LOG.debug('Initial DB status checked and phone home message sent: %s', message)
            except Exception as err:
                LOG.error("Failed to connect to MQ due to channel not available: %s", err)
                pass
        else:
            # apply snapshot if the instance is configured to do so
            result = self.handler.apply_db_snapshot(snapshot_conf['snapshot_uri'],
                                                    snapshot_conf['swift_auth_user'],
                                                    snapshot_conf['swift_auth_key'],
                                                    snapshot_conf['swift_auth_url'])
            try:
                self.messaging.phone_home(result)
                LOG.debug('Initial snapshot applied and phone home message sent: %s', result)
            except Exception as err:
                LOG.error("Failed to connect to MQ due to channel not available: %s", err)
                pass
        # start listening and consuming rpc messages from API Server
        try:
            self.messaging.start_consuming()
        except Exception as err:
            LOG.error("Error processing RPC request: %s", err)
            pass

    def create_database_instance(self, msg):
        """ This will call the method that creates a database instance"""
        LOG.debug('Functionality not implemented')
        result = None
        return result

    def delete_database_instance(self, msg):
        """ This will call the method that deletes a database instance"""
        LOG.debug('Functionality not implemented')
        result = None
        return result

    def create_database(self, msg):
        """ This calls the method that deletes a database schema"""
        result = self.handler.create_database(msg['args']['database'])
        return result

    def restart_database(self, msg):
        """ This restarts MySQL for reading conf changes"""
        result = call("sudo service mysql restart", shell=True)
        return result

    def restart_database_instance(self, msg):
        """ This will call the method that restarts the database instance """
        LOG.debug('Functionality not implemented')
        result = None
        return result

    def reset_password(self, msg):
        """ This calls the method that changes the user password """ 
        result = self.handler.reset_user_password(
            self.agent_username, msg['args']['password'])
        return result

    def create_user(self, msg):
        """ This calls the method that creates a given database user """
        result = self.handler.create_user(
            msg['args']['username'], 
            msg['args']['hostname'],
            msg['args']['password'])
        return result

    def delete_user(self, msg):
        """ This calls the method that deletes a database user """
        result = self.handler.delete_user(msg['args']['username'])
        return result

    def take_database_snapshot(self, msg):
        """ This will call the method that creates a database snapshot """
        result = self.handler.create_db_snapshot(msg['args']['sid'],
                                                 msg['args']['credential']['user'], 
                                                msg['args']['credential']['key'], 
                                                msg['args']['credential']['auth'])
        self.messaging.phone_home(result)

    def apply_database_snapshot(self, msg):
        print "process touches here"

        result = self.handler.apply_db_snapshot(msg['args']['storage_path'], 
                                                msg['args']['credential']['user'], 
                                                msg['args']['credential']['key'], 
                                                msg['args']['credential']['auth'])
        
        self.messaging.phone_home(result)
        
    def check_status(self):
        """ This calls the method to check MySQL's running status """
        if self.checker.check_if_running(sleep_time_seconds=3,
            number_of_checks=5):
            result = ResultState.RUNNING
        else:
            result = ResultState.NOSTATE
        return result

    def get_system_info(self):
        """ This calls the method to get system OS information """
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
        
        # The following is a dispatcher 
        # TODO: use pythonic solution with dictionary of methods
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
        elif method == 'create_snapshot':
            result = self.take_database_snapshot(msg)
        elif method == 'apply_snapshot':
            result = self.apply_database_snapshot(msg)
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
    agent = SmartAgent()
    # act according to argument supplied
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            agent.start()
        elif 'stop' == sys.argv[1]:
            agent.stop()
        elif 'restart' == sys.argv[1]:
            agent.restart()
        elif 'run' == sys.argv[1]:
            agent.run()
        else:
            print "unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "Usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)


if __name__ == '__main__':
    main()
