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
import _mysql  # see http://mysql-python.sourceforge.net/MySQLdb.html
from singleton import Singleton
import logging
logging.basicConfig()

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

@Singleton
class DatabaseManager:
    """
    This class encapsulates a (singleton) connection to a database.
    """
    def __init__(self,
                 host_name='localhost',
                 database_name='mysql',
                 config_file='~/.my.cnf'):
        self.host_name = host_name
        self.database_name = database_name
        self.config_file = config_file
        self._database_connection = None

    def __del__(self):
        self.close_connection()

    def open_connection(self):
        if self._database_connection:
            LOG.debug("Database connection already opened")
            return  # already connected
        try:
            LOG.debug('Connecting to database')
            connection = _mysql.connect(host=self.host_name,
                db=self.database_name,
                read_default_file=self.config_file)
        except:
            LOG.error('Error connecting to the database: %s',
                str(sys.exc_info()[0]))
        else:
            self._database_connection = connection
        return

    def close_connection(self):
        if self._database_connection:
            try:
                self._database_connection.close()
            except:
                LOG.error('Error closing database connection: %s',
                    str(sys.exc_info()[0]))
                return False
            else:
                return True
        return False

    def status(self):
        if not self._database_connection:
            self.open_connection()
        if self._database_connection:
            return self._database_connection.stat()
        else:
            return ''

    def execute_sql_commands(self,
                             commands):
        assert self._database_connection
        try:
            for command in commands:
                self._database_connection.query(command)
        except:
            LOG.error('Database error while executing %s: %s',
                command, str(sys.exc_info()[0]))
        return
