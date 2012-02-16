#!/usr/bin/python

# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
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

import _mysql
from smartagent_persistence import DatabaseManager
import logging
import random
from result_state import ResultState

logging.basicConfig()

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

def random_string(size=6):
    """ Generate a random string to be used for password """
    # string to use
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    # join random chars of size N and return
    return ''.join(random.choice(chars) for x in range(size))

def write_dotmycnf(user='os_admin', password='hpcs'):
    """ Write the .my.cnf file so as the user does not require credentials 
    for the DB """
    # open and write .my.cnf
    mycf = open ('/root/.my.cnf', 'w')
    mycf.write( "[client]\nuser={}\npassword={}" . format(user, password))
  

class MysqlCommandHandler:
    """ Class for passing commands to mysql """
    
    def __init__(self, host_name='15.185.175.59',
                 database_name='mysql', config_file='~/.my.cnf'):
        self.persistence_agent = DatabaseManager(host_name=host_name
            , database_name=database_name, config_file=config_file)
        self.persistence_agent.open_connection()

    def create_user(self, username, host='localhost',
                    newpassword=random_string()):
        """ create a new user """
        result = ResultState.NO_CONNECTION
        sql_commands = []

        # Prepare SQL query to UPDATE required records
        sql_create = \
        "grant all privileges on *.* to '%s'@'%s' identified by '%s'"\
        % (username, host, newpassword)
        sql_commands.append(sql_create)
       
        # Open database connection
        try:
            self.persistence_agent.execute_sql_commands(sql_commands)
            result = ResultState.SUCCESS
        except _mysql.Error:
            result = ResultState.FAILED
            LOG.error("Reset user password failed")
        return result

    def delete_user(self, username):
        """ delete the user, all grants """
        result = ResultState.NO_CONNECTION
        sql_commands = []
        
        # Prepare SQL query to UPDATE required records
        sql_delete = \
        "delete from mysql.user where User = '%s'" % (username)
        sql_flush = "FLUSH PRIVILEGES"
        sql_commands.append(sql_delete)
        sql_commands.append(sql_flush)
       
        # Open database connection
        try:
            self.persistence_agent.execute_sql_commands(sql_commands)
            result = ResultState.SUCCESS
        except _mysql.Error:
            result = ResultState.FAILED
            LOG.error("delete user '%s' failed" % (username))
        return result

    def delete_user_host(self, username, host):
        """ delete the user, specific user@host grant """
        result = ResultState.NO_CONNECTION
        
        # Prepare SQL query to UPDATE required records
        sql_delete = \
        "drop user '%s'@'%s'" % (username, host)
        sql_commands = []
        sql_commands.append(sql_delete)
       
        # Open database connection
        try:
            self.persistence_agent.execute_sql_commands(sql_commands)
            result = ResultState.SUCCESS
        except _mysql.Error:
            result = ResultState.FAILED
            LOG.error("delete user '%s'@'%s' failed" % (username, host))
        return result

    def reset_user_password(self, username='root', newpassword='something'):
        """ reset the user's password """
        result = ResultState.NO_CONNECTION
        
        # Prepare SQL query to UPDATE required records
        sql_update = \
        "update mysql.user set Password=PASSWORD('%s') WHERE User='%s'"\
        % (newpassword, username)
        sql_flush = "FLUSH PRIVILEGES"
        sql_commands = []
        sql_commands.append(sql_update)
        sql_commands.append(sql_flush)
       
        # Open database connection
        try:
            self.persistence_agent.execute_sql_commands(sql_commands)
            result = ResultState.SUCCESS
        except _mysql.Error:
            result = ResultState.FAILED
            LOG.error("Reset user password failed")
        return result

    def reset_agent_password(self, username='os_admin', newpassword='hpcs'):
        """ Reset the MySQL account password for the agent's account """ 
        result = ResultState.NO_CONNECTION
        # generate a password
        newpassword = random_string(16)

        # SQL statement to change agent password 
        sql = "SET PASSWORD FOR '%s'@'localhost'"\
        " PASSWORD('%s')" % (username, newpassword)
        sql_commands = []
        sql_commands.append(sql)
       
        # Open database connection
        try: 
            # Execute the SQL command
            self.persistence_agent.execute_sql_commands(sql_commands)
            result = ResultState.SUCCESS
            # write the .my.cnf for the agent user so the agent can connect 
            write_dotmycnf(username, newpassword)
            
        except _mysql.Error:
            result = ResultState.FAILED
            LOG.error("Reset agent password failed")

        return result

    def create_database(self, database):
        """ Create a database """
        # ensure the variable database is set
        try:
            database 
        except NameError:
            result = ResultState.FAILED
            LOG.error("Create database failed : no database defined")
            return result

        result = ResultState.NO_CONNECTION
        
        sql_create = \
        "create database `%s`" % (database)
        sql_commands = []
        sql_commands.append(sql_create)
       
        # Open database connection
        try:
            self.persistence_agent.execute_sql_commands(sql_commands)
            result = ResultState.SUCCESS
        except _mysql.Error:
            result = ResultState.FAILED
            LOG.error("Create database failed")
        return result

    def drop_database(self, database):
        """ Drop a database """
        # ensure the variable database is set
        try:
            database 
        except NameError:
            result = ResultState.FAILED
            LOG.error("Drop database failed : no database defined")
            return result

        result = ResultState.NO_CONNECTION
        
        sql_drop = \
        "drop database `%s`" % (database)
        sql_commands = []
        sql_commands.append(sql_drop)
       
        # Open database connection
        try:
            self.persistence_agent.execute_sql_commands(sql_commands)
            result = ResultState.SUCCESS
        except _mysql.Error:
            result = ResultState.FAILED
            LOG.error("Drop database failed")
        return result


def main():
    """ main program """
    handler = MysqlCommandHandler()
    handler.reset_user_password('root', 'hpcs')

if __name__ == '__main__':
    main()
