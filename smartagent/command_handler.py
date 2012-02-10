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

class MysqlCommandHandler:
    
    def __init__(self, hostname='15.185.173.212',
                 dbname='mysql', config_file='~/.my.cnf'):
        self.hostname = hostname
        self.db = dbname
        self.config_file = config_file


    def reset_user_password(self, username='root', newpassword='something'):
        
        # Prepare SQL query to UPDATE required records
        sql = "update mysql.user set Password=PASSWORD('%s') WHERE User='%s'" % (newpassword, username)
        sql_ = "FLUSH PRIVILEGES"
       
        # Open database connection
        try: 
            # Open database connection
            con = _mysql.connect(host=self.hostname, db=self.db,
                                 read_default_file=self.config_file)
            # Execute the SQL command
            con.query(sql)
            con.query(sql_)
            # disconnect from server
            con.close()
        except _mysql.Error:
            print "Error: reset user password failed"
       
            
def main():
    handler = MysqlCommandHandler()
    handler.reset_user_password('root', 'hpcs')

if __name__ == '__main__':
    main()
