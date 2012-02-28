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
import tarfile

from os import environ
import swift 
import socket
from check_mysql_status import MySqlChecker

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
            
    
    def get_response_body(self, container, path_specifier, result, snapshot_size=0):
        #temp = 'mysql-backup' + '/' + path_specifier + '.tar.gz'
        if result == ResultState.SUCCESS:
            temp_file_name = '%s%s' % (os.path.join(container, path_specifier), '.tar.gz')
        else:
            temp_file_name = 'N/A'
        
        return {"method": "update_snapshot_state", 
                "args": {"sid": path_specifier, 
                         "state": result, 
                         "storage_uri": temp_file_name,
                         "storage_size": snapshot_size }}

    def create_tar_file(self, path, tar_name):
        try:
            #target_name = tar_name + '.tar.gz'
            target_name = '%s%s' % (tar_name, '.tar.gz')
            with tarfile.open(target_name, 'w:gz') as tar_file:
                tar_file.add(path)
            fully_qualified_target_name = '/root/' + target_name
#            print os.path.exists(target)
#            print tarfile.is_tarfile(target_name)
            
#            return target_name
        
            
#            target = '/root/' + target_name
            
            if not os.path.exists(fully_qualified_target_name):
                LOG.debug('tar file does not exist: %s',
                    fully_qualified_target_name)
                raise
            if not tarfile.is_tarfile(target_name):
                LOG.debug('tar file not an archive: %s', target_name)
                raise
            else:
                return target_name
        except Exception as tarfile_exception:
            LOG.error('tar/compress snapshot failed somehow: %s',
                tarfile_exception)
            return ResultState.FAILED
        
    def keyword_checker(self, keyword_to_check, log_path):
        try:
            with open(log_path, "r") as f:
                last_lines = f.readlines()[-1:]
        
            for line in last_lines:
                if keyword_to_check in line:
                    LOG.debug("innobackupex runs successfully; read: %s",
                        line)
                    return ResultState.SUCCESS
                else:
                    LOG.error("innobackupex run failed; read: %s ",
                        line)
                    return ResultState.FAILED
        except:
            LOG.error("log file does not exist: %s", log_path)
            
            
    def check_process(self, proc):
        status = proc.poll()
        iteration = 0
        TIME_OUT = 8640 # time out after 12 hours = 60 * 60 * 12 / 5
        
        while status !=0 and iteration < TIME_OUT:
            iteration = iteration + 1
            if status == None:
                LOG.debug('subprocess is still alive; iteration: %d', iteration)
                time.sleep(5)
                status = proc.poll()
            else:
                LOG.error('subprocess encounter errors, exit code: %s' % status)
                return 'error'
        if iteration == TIME_OUT:
            return 'timed out'
        else:
            return 'normal'
    
    def create_db_snapshot(self, container, path_specifier):
        path = os.path.join(self.backup_path, path_specifier)
        log_home = os.path.join(self.backlog_path, path_specifier)
        keyword_to_check = "innobackupex: completed OK!"  # TODO: replace with regexp?
        
        result = None
        """ create backup snapshot first """
        
        log_path = '%s%s' % (log_home, '_innobackupex_create.log')
        inno_backup_cmd = "innobackupex --no-timestamp %s > %s 2>&1" % (path, log_path)

        try:
            proc = subprocess.Popen(inno_backup_cmd, shell=True)
        except (OSError, ValueError) as ex_oserror:
            LOG.error('popen exception caught: %s', ex_oserror)
        except Exception as ex:
            LOG.error('popen exception caught: %s', ex)
        else:
            if self.check_process(proc) != 'normal':
                LOG.error('create snapshot failed somehow')
                return self.get_response_body(container,
                    path_specifier,
                    ResultState.FAILED)
        
        result = self.keyword_checker(keyword_to_check, log_path)
        if result != ResultState.SUCCESS:
            LOG.error('snapshot is not ready for preparation')
            return self.get_response_body(container,
                path_specifier,
                ResultState.FAILED)

        """ prepare the snapshot for uploading to swift """
        
        log_path = '%s%s' % (log_home, '_innobackupex_prepare.log')
            
        inno_prepare_cmd = "innobackupex --use-memory=1G --apply-log %s > %s 2>&1" % (path, log_path)

        try:
            proc = subprocess.Popen(inno_prepare_cmd, shell=True)
        except (OSError, ValueError) as ex_oserror:
            LOG.error('popen exception caught: %s', ex_oserror)
        except Exception as ex:
            LOG.error('popen exception caught: %s', ex)
        else:
            if self.check_process(proc) != 'normal':
                LOG.error('preparation failed somehow')
                return self.get_response_body(container, path_specifier, ResultState.FAILED)
            
        result = self.keyword_checker(keyword_to_check, log_path)
        if result != ResultState.SUCCESS:
            LOG.error('preparation encounter exceptions or errors')
            return self.get_response_body(container,
                path_specifier,
                ResultState.FAILED)
        
        """ tar the entire backup folder """
        try:
            tar_result = self.create_tar_file(path, path_specifier)
            LOG.debug('tar result: %s', tar_result)
            if tar_result == ResultState.FAILED:
                return self.get_response_body(container,
                    path_specifier,
                    ResultState.FAILED,
                    self.get_snapshot_size(tar_result))

            """ start upload to swift """
            opts = {'auth' : environ.get('ST_AUTH'),
                    'user' : environ.get('ST_USER'),
                    'key' : environ.get('ST_KEY'),
                    'snet' : False,
                    'prefix' : '',
                    'auth_version' : '1.0'}

            try:
                cont = swift.st_get_container(opts, container)
                if len(cont) == 0:
                    # create container
                    swift.st_create_container(opts, container)
                swift.st_upload(opts, container, tar_result)
            except (swift.ClientException, HTTPException, socket.error), err:
                LOG.error('Failed to create the container: %s', err)
                return self.get_response_body(container,
                    path_specifier,
                    ResultState.FAILED,
                    self.get_snapshot_size(tar_result))
            else:
                response_body = self.get_response_body(container,
                    path_specifier,
                    ResultState.SUCCESS,
                    self.get_snapshot_size(tar_result))
        finally:  # create_tar_file
            """ remove .tar.gz file after upload """
            try:
                if os.path.isfile(tar_result):
                    os.remove(tar_result)
            except Exception as ex:
                LOG.error('Exception while removing tar file: %s', ex)

        LOG.debug(response_body)
        return response_body
    
    def restart_database(self):
        """ This restarts MySQL for reading conf changes"""
        try: 
            proc = subprocess.call("sudo service mysql restart", shell=True)
        except (OSError, ValueError) as ex_oserror:
            LOG.error('CALL exception caught: %s', ex_oserror)
            return ResultState.FAILED
        except Exception as ex:
            LOG.error('CALL exception caught: %s', ex)
            return ResultState.FAILED
        else:
            if self.check_process(proc) != 'normal':
                LOG.error('restart mysql failed somehow')
                return ResultState.FAILED
            return self.checker.check_if_running(sleep_time_seconds=3, number_of_checks=5)
    

    def stop_database(self):
        """ This stop MySQL """
        try:
            proc = subprocess.call("sudo service mysql stop", shell=True)
        except (OSError, ValueError) as ex_oserror:
            LOG.error('CALL exception caught: %s', ex_oserror)
            return ResultState.FAILED
        except Exception as ex:
            LOG.error('CALL exception caught: %s', ex)
            return ResultState.FAILED
        else:
            if self.check_process(proc) != 'normal':
                LOG.error('restart mysql failed somehow')
                return ResultState.FAILED
            return not self.checker.check_if_running(sleep_time_seconds=3, number_of_checks=5)
        
    def start_database(self):
        """ This start MySQL for reading conf changes"""
        try:
            proc = subprocess.call("sudo service mysql start", shell=True)
        except (OSError, ValueError) as ex_oserror:
            LOG.error('CALL exception caught: %s', ex_oserror)
            return ResultState.FAILED
        except Exception as ex:
            LOG.error('CALL exception caught: %s', ex)
            return ResultState.FAILED
        else:
            if self.check_process(proc) != 'normal':
                LOG.error('restart mysql failed somehow')
                return ResultState.FAILED
            return self.checker.check_if_running(sleep_time_seconds=3, number_of_checks=5)
    
    def apply_db_snapshot(self, uri, st_user, st_key, st_auth):
        """ stop mysql server """
        if not self.stop_database():
            return ResultState.FAILED
        
        """ push the current data to history folder """
        """ download snapshot from swift """
        """ decompress snapshot """
        """ restart mysql """
        if not self.start_database():
            return ResultState.FAILED
        
def main():
    """ main program """
    handler = MysqlCommandHandler()
#    handler.reset_user_password(this_variable_should_be_username_of_tenant, 'hpcs')
    # TODO: make sure to get this from API!
    handler.create_db_snapshot(container='mysql-backup-dbasdemo', path_specifier='uuid2')

if __name__ == '__main__':
    main()
