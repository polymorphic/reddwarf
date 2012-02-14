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
import string
import random

logging.basicConfig()

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

class StateTable:
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    NO_CONNECTION = "NO_CONNECTION"
    

class MysqlCommandHandler:
    
    def __init__(self, host_name='15.185.175.59',
                 database_name='mysql', config_file='~/.my.cnf'):
        self.persistence_agent = DatabaseManager(host_name=host_name
            , database_name=database_name, config_file=config_file)
        self.persistence_agent.open_connection()

    def reset_user_password(self, username='root', newpassword='something'):
        
        result = StateTable.NO_CONNECTION
        
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
            result = StateTable.SUCCESS
        except _mysql.Error:
            result = StateTable.FAILED
            LOG.error("Reset user password failed")
        return result

#    def reset_agent_password(self, username='os_admin', newpassword='hpcs'):
#        
#        result = StateTable.NO_CONNECTION
#        # generate a password
#        newpassword = self.random_string(16)
#
#        # SQL statement to change agent password 
#        sql = "SET PASSWORD FOR 'os_admin'@'localhost' = PASSWORD('%s')" % (newpassword)
#       
#        # Open database connection
#        try: 
#            # Execute the SQL command
#            self.persistence_agent.execute_sql_commands(sql)
#            result = StateTable.SUCCESS
#            # write the .my.cnf for the agent user so the agent can connect 
#            self.write_temp_mycnf_with_admin_account('os_admin', newpassword)
#            
#        except _mysql.Error:
#            result = StateTable.FAILED
#            LOG.error("Reset agent password failed")
#
#    def random_string(self, size=6, chars=string.ascii_uppercase + string.digits):
#
#        # join random chars of size N and return
#        return ''.join(random.choice(chars) for x in range(size))
#
#    def write_temp_mycnf_with_admin_account(user='os_admin', password='hpcs'):
#
#        # open and write .my.cnf
#        mycf = open ('/root/.my.cnf', 'w')
#        mycf.write( "[client]\nuser={}\npassword={}" . format(user, password))

def main():
    handler = MysqlCommandHandler()
    handler.reset_user_password('root', 'hpcs')

if __name__ == '__main__':
    main()
