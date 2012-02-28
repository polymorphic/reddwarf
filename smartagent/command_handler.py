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
import os
import time
import subprocess

from os import environ
import swift 
import socket

try:
    from eventlet.green.httplib import HTTPException, HTTPSConnection
except ImportError:
    from httplib import HTTPException, HTTPSConnection
    


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
    # TODO: get rid of hard-code - directory should be configurable
    cnf_file_name = os.path.join(environ['HOME'], '.my.cnf')
    try:
        with open (cnf_file_name, 'w') as mycf:
            mycf.write( "[client]\nuser={}\npassword={}" . format(user, password))
    except OSError as os_error:
        LOG.error('Error writing .cnf file: %s', os_error)
  
class MysqlCommandHandler:
    """ Class for passing commands to mysql """
    
    # TODO: why this IP address? Hardcode not good
    #def __init__(self, host_name='15.185.175.59',
    def __init__(self,
                 host_name='localhost',
                 database_name='mysql',
                 config_file='~/.my.cnf'):
        self.persistence_agent = DatabaseManager(host_name=host_name
            , database_name=database_name,
            config_file=config_file)
        self.persistence_agent.open_connection()
        
        """ sanity check for log folder existence """
        self.backlog_path = '/home/nova/backup_logs/'
        self.backup_path = '/var/lib/mysql-backup/'
        
        if not os.path.exists(self.backlog_path):
             try:
                 os.makedirs(self.backlog_path)
             except OSError, e:
                 LOG.debug("There was an error creating %s",
                     self.backlog_path)

    def create_user(self,
                    username,
                    host='localhost',
                    newpassword=random_string()):
        """ create a new user """
        sql_commands = []

        # Prepare SQL query to UPDATE required records
        sql_create = \
            "grant all privileges on *.* to '%s'@'%s' identified by '%s'"\
            % (username, host, newpassword)
        sql_commands.append(sql_create)

        try:
            #  connection opened in __init__
            self.persistence_agent.execute_sql_commands(sql_commands)
            result = ResultState.SUCCESS
        except _mysql.Error as error:
            result = ResultState.FAILED
            LOG.error("Reset user password failed: %s", error)
        return result

    def delete_user(self, username):
        """ delete the user, all grants """
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
            LOG.error("delete user '%s' failed", username)
        return result

    def delete_user_host(self, username, host):
        """ delete the user, specific user@host grant """
        
        # Prepare SQL query to UPDATE required records
        sql_delete = \
            "drop user '%s'@'%s'" % (username, host)
        sql_commands = []
        sql_commands.append(sql_delete)
       
        # Open database connection
        try:
            self.persistence_agent.execute_sql_commands(sql_commands)
            result = ResultState.SUCCESS
        except _mysql.Error as error:
            result = ResultState.FAILED
            LOG.error("delete user '%s'@'%s' failed: %s", username, host,
                error)
        return result


    # TODO: user password, not the root user - make sure to not change root user password
    def reset_user_password(self,
                            username='do not default!',
                            newpassword='something'):
        """ reset the user's password """
        
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
            LOG.debug("Executing SQL command: %s", sql_commands)
            self.persistence_agent.execute_sql_commands(sql_commands)
            result = ResultState.SUCCESS
        except Exception as error:
            result = ResultState.FAILED
            LOG.error("Reset user password failed: %s", error)
        return result

    def reset_agent_password(self, username='os_admin', newpassword='hpcs'):
        """ Reset the MySQL account password for the agent's account """
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
            
        except _mysql.Error as error:
            result = ResultState.FAILED
            LOG.error("Reset agent password failed: %s", error)

        return result

    def create_database(self, database):
        """ Create a database """
        # ensure the variable database is set
        if database is None:
            result = ResultState.FAILED
            LOG.error("Create database failed : no database defined")
            return result
        
        sql_create = \
        "create database `%s`" % (database)
        sql_commands = []
        sql_commands.append(sql_create)
       
        # Open database connection
        try:
            self.persistence_agent.execute_sql_commands(sql_commands)
            result = ResultState.SUCCESS
        except _mysql.Error as error:
            result = ResultState.FAILED
            LOG.error("Create database failed: %s", error)
        return result

    def drop_database(self, database):
        """ Drop a database """
        # ensure the variable database is set
        if database is None:
            result = ResultState.FAILED
            LOG.error("Drop database failed : no database defined")
            return result

        sql_drop = \
        "drop database `%s`" % (database)
        sql_commands = []
        sql_commands.append(sql_drop)
       
        # Open database connection
        try:
            self.persistence_agent.execute_sql_commands(sql_commands)
            result = ResultState.SUCCESS
        except _mysql.Error as error:
            result = ResultState.FAILED
            LOG.error("Drop database failed: %s", error)
        return result

    # TODO: dragos to code-review below this line

    def get_snapshot_size(self, path):
        return os.path.getsize(path)
#        snapshot_size = 0
#        for (path, dirs, files) in os.walk(path):
#            for file in files:
#                filename = os.path.join(path, file)
#                snapshot_size += os.path.getsize(filename)
#        return snapshot_size
            
    
    def get_response_body(self, path_specifier, result, snapshot_size):
        temp = 'mysql-backup' + '/' + path_specifier + '.tar.gz'
        return {"method": "update_snapshot_state", 
                "args": {"sid": path_specifier, 
                         "state": result, 
                         "storage_uri": temp, 
                         "storage_size": snapshot_size }}

    def get_tar_file(self, path, tar_name):
        try:
            target_name = tar_name + '.tar.gz'
            tar = tarfile.open(target_name, 'w:gz')
            tar.add(path)
            tar.close()
            target = '/root/' + target_name
#            print os.path.exists(target)
#            print tarfile.is_tarfile(target_name)
            
            return target_name
        
            
#            target = '/root/' + target_name
#            
#            if not os.path.exists(target):
#                raise
#            if not tarfile.is_tarfile(target_name):
#                raise
#            else:
#                return target_name
        except:
            LOG.error('tar/compress snapshot failed somehow')
            return ResultState.FAILED
        
    def keyword_checker(self, keyword_to_check, log_path):
        try: 
            f = open(log_path, "r")
            last_lines = f.readlines()[-1:]
        
            for line in last_lines:
                if keyword_to_check in line:
                    LOG.debug("innobackupex runs successfully")
                    return ResultState.SUCCESS
                else:
                    LOG.error("innobackupex run failed")
                    return ResultState.FAILED
        except:
            LOG.error("log file does not exist")
            
            
    def check_process(self, proc):
        status = proc.poll()
        while status !=0:
            if status == None:
                LOG.debug('subprocess is still alive')
                time.sleep(5)
                status = proc.poll()
            else:
                LOG.error('subprocess encounter errors, exit code: %s' % status)
                return 'error'
        return 'normal'
    
    # TODO: container MUST come from API! Change this.
    def create_db_snapshot(self, path_specifier):
        path = self.backup_path + path_specifier
        log_home = self.backlog_path + path_specifier + '_'
        keyword_to_check = "innobackupex: completed OK!"
        
        result = None
        """ create backup snapshot first """
        
        log_path = log_home + 'innobackupex_create.log'
        inno_backup_cmd = "innobackupex --no-timestamp %s > %s 2>&1" % (path, log_path)

        proc = subprocess.Popen(inno_backup_cmd, shell=True)

        if self.check_process(proc) == 'error':
            LOG.error('create snapshot failed somehow')
            return self.get_response_body(path_specifier, ResultState.FAILED, 0)
        
        result = self.keyword_checker(keyword_to_check, log_path) 
        if result != ResultState.SUCCESS:
            LOG.error('snapshot is not ready for preparation')
            return self.get_response_body(path_specifier, ResultState.FAILED, 0)

        """ prepare the snapshot for uploading to swift """
        
        log_path = log_home + 'innobackupex_prepare.log'
            
        inno_prepare_cmd = "innobackupex --use-memory=1G --apply-log %s > %s 2>&1" % (path, log_path)
            
        proc_ = subprocess.Popen(inno_prepare_cmd, shell=True)
        if self.check_process(proc_) == 'error':
            LOG.error('preparation failed somehow')
            return self.get_response_body(path_specifier, ResultState.FAILED, 0)
        
        """ tar the entire backup folder """
        tar_result = self.get_tar_file(path, path_specifier)
        print tar_result
        if tar_result == ResultState.FAILED:
            return self.get_response_body(path_specifier, ResultState.FAILED, self.get_snapshot_size(path))
        
        """ start upload to swift """
        opts = {'auth' : environ.get('ST_AUTH'),
            'user' : environ.get('ST_USER'),
            'key' : environ.get('ST_KEY'),
            'snet' : False,
            'prefix' : '',
            'auth_version' : '1.0'}
        try:
            swift.st_upload(opts, 'mysql-backup', tar_result)  
        except(ClientException, HTTPException, socket.error), err:
            LOG.error(str(err))
            return self.get_response_body(path_specifier, ResultState.FAILED, self.get_snapshot_size(path))
         
        response_body = self.get_response_body(path_specifier, 
                        ResultState.SUCCESS, 
                        self.get_snapshot_size(tar_result))
        LOG.debug(response_body)
        
        """ remove .tar.gz file after upload """
        try:
            os.remove(tar_result)
        except:
            print tar_result
            print 'remove .tar.gz does not work'
            pass
        
        return response_body
        
def main():
    """ main program """
    handler = MysqlCommandHandler()
#    handler.reset_user_password(this_variable_should_be_username_of_tenant, 'hpcs')
    # TODO: make sure to get this from API!
    handler.create_db_snapshot(container='mysql-backup-dbasdemo', path_specifier='uuid2')

if __name__ == '__main__':
    main()
