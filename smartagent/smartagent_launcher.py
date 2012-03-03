#!/usr/bin/env python

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
import os
import signal
import daemon
import lockfile
import logging
import sys
import time
from service import Service

__author__ = 'dragosmanolescu'
__email__ = 'dragosm@hp.com'
__python_version__ = '2.7.2'

logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)

WORKING_DIR = '/Users/dragosmanolescu/tmp'  #TODO: change
PID_FILENAME = os.path.join(WORKING_DIR, 'smartagent.pid')  #TODO: refactor

def main():
    """Activates the smart agent by instantiating an instance of SmartAgent
       and then calling its start_consuming() method."""


    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            start()
        elif 'stop' == sys.argv[1]:
            stop()
        elif 'restart' == sys.argv[1]:
            restart()
        elif 'run' == sys.argv[1]:
            start()
        else:
            print "unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "Usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)

def start():
    pid = _get_daemon_pid()
    if pid:
        if _is_process_running(pid):
            LOGGER.error('smartagent daemon already running')
            sys.exit(os.EX_USAGE)
        else:
            # stale PID file
            os.remove(PID_FILENAME)
    LOGGER.debug('setting up the daemon')
    smart_agent_service = Service(WORKING_DIR)
    context = daemon.DaemonContext(
        working_directory=WORKING_DIR,
        pidfile=lockfile.FileLock(str(os.path.join(WORKING_DIR,
            'smartagent_launcher'))))
    context.signal_map = {
        signal.SIGTERM: smart_agent_service.shutdown,
        signal.SIGHUP: smart_agent_service.restart  #TODO: implement
        }
    smart_agent_service.setup()
    try:
        with context:  # daemonize
            smart_agent_service.start()
            # launcher process ends here
    except lockfile.Error as le:
        print('LockError: %s' % le)

def _get_daemon_pid():
    if not os.path.isfile(PID_FILENAME):
        return None
    with open(PID_FILENAME, 'r') as pid_file:
        pid_string = pid_file.read().strip()
    try:
        pid = int(pid_string)
    except ValueError:
        return None
    return pid

def _is_process_running(pid):
    try:
        os.kill(pid,0)
    except OSError as os_error:
        return False
    else:
        return True

def stop():
    pid = _get_daemon_pid()
    if pid:
        if _is_process_running(pid):
            # process running
            try:
                for i in range(1,10):
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(1)
                LOGGER.error("Can't kill daemon (PID %d)", pid)
                sys.exit(os.EX_OSERR)
            except OSError as os_error:
                pass
        else:
            # stale PID file
            os.remove(PID_FILENAME)
        assert(not os.path.isfile(PID_FILENAME))
    else:
        LOGGER.error("No/invalid PID file")
        sys.exit(os.EX_OSFILE)


def restart():
    pid = _get_daemon_pid()
    if pid:
        try:
            os.kill(pid, signal.SIGHUP)
        except OSError as os_error:
            LOGGER.error("Can't restart daemon (PID %d)", pid)
            sys.exit(os.EX_OSERR)
    else:
        LOGGER.error("No/invalid PID file")
        sys.exit(os.EX_OSFILE)

def status():
    pass  #TODO: implement

if __name__ == '__main__':
    main()

