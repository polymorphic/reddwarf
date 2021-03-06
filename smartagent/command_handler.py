#!/usr/bin/python

# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 HP Software, LLC
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
import paths
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
try:
    import swift
except Exception:
    pass
import socket
import string

from check_mysql_status import MySqlChecker

try:
    from eventlet.green.httplib import HTTPException, HTTPSConnection
except ImportError:
    from httplib import HTTPException, HTTPSConnection

LOG = logging.getLogger(paths.smartagent_name)

def random_string(size=6):  # TODO: move to utils.py
    """ Generate a random string to be used for password """
    # string to use
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    # join random chars of size N and return
    return ''.join(random.choice(chars) for x in range(size))

def write_dotmycnf(user='os_admin', password='hpcs'):  # TODO: move to class/utils.py
    """ Write the .my.cnf file so as the user does not require credentials
    for the DB """
    # open and write .my.cnf
    cnf_file_name = os.path.join(paths.mycnf_base, '.my.cnf')
    try:
        with open (cnf_file_name, 'w') as mycf:
            mycf.write( "[client]\nuser={}\npassword={}" . format(user, password))
    except OSError as os_error:
        LOG.error('Error writing .cnf file: %s', os_error)

class MysqlCommandHandler:
    """ Class for passing commands to mysql """

    # TODO: extract to paths.py
    def __init__(self,
                 host_name='localhost',
                 database_name='mysql',
                 config_file=os.path.join(paths.mycnf_base, '.my.cnf')):
        self.persistence_agent = DatabaseManager(host_name=host_name,
            database_name=database_name,
            config_file=config_file)
        self.persistence_agent.open_connection()
        self.checker = MySqlChecker()

        if not os.path.exists(paths.backlog_path):
             try:
                 os.makedirs(paths.backlog_path)
             except OSError, e:
                 LOG.debug("There was an error creating %s",
                     paths.backlog_path)

    def create_user(self,
                    username,
                    host='localhost',
                    newpassword=random_string()):
        # create a new user
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
            "delete from mysql.user where User = '%s'" % username
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
        sql_commands = [sql_delete]

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
                            username='dbas',
                            newpassword='something'):
        """ reset the user's password """

        # Prepare SQL query to UPDATE required records
        sql_update = \
            "update mysql.user set Password=PASSWORD('%s') WHERE User='%s'"\
            % (newpassword, username)
        sql_flush = "FLUSH PRIVILEGES"
        sql_commands = [sql_update, sql_flush]

        # Open database connection
        try:
            self.persistence_agent.execute_sql_commands(sql_commands)
            result = ResultState.SUCCESS
        except _mysql.Error as error:
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
        sql_commands = [sql]

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
        "create database `%s`" % database
        sql_commands = [sql_create]

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
        "drop database `%s`" % database
        sql_commands = [sql_drop]

        # Open database connection
        try:
            self.persistence_agent.execute_sql_commands(sql_commands)
            result = ResultState.SUCCESS
        except _mysql.Error as error:
            result = ResultState.FAILED
            LOG.error("Drop database failed: %s", error)
        return result

    def get_snapshot_size(self, path):
        return os.path.getsize(path)
#        snapshot_size = 0
#        for (path, dirs, files) in os.walk(path):
#            for file in files:
#                filename = os.path.join(path, file)
#                snapshot_size += os.path.getsize(filename)
#        return snapshot_size


    def get_response_body_for_create_snapshot(self, container, path_specifier, result, snapshot_size=0):
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

    def get_leading_path(self, path):
        #print path
        directs = path.split('/')
        #print directs
        leading_path =''
        for direct in directs:
            leading_path = os.path.join(leading_path, direct)

        #print '%s/' % leading_path
        return '%s/' % leading_path

    def create_tar_file(self, path, tar_name):
        try:
            target_name = '%s%s' % (tar_name, '.tar.gz')
            leading_path = self.get_leading_path(path)
            LOG.debug('the leading path for tar file is %s', leading_path)
            with tarfile.open(target_name, 'w:gz') as tar:
                for (path, dirs, files) in os.walk(path):
                    for file in files:
                        filename = os.path.join(path, file)
                        final_member_name = filename.replace(leading_path, '')
                        #LOG.debug('final_member_name: %S', final_member_name)
                        #tar.add(name=filename, recursive=False)
                        tar.add(name=filename, arcname=final_member_name)
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
        except Exception:
            LOG.error("log file does not exist: %s", log_path)


    def check_process(self, proc):
        status = proc.poll()
        iteration = 0
        TIME_OUT = 8640 # time out after 12 hours = 60 * 60 * 12 / 5

        while status !=0 and iteration < TIME_OUT:
            iteration = iteration + 1
            if status is None:
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

    def create_db_snapshot(self, path_specifier, st_user, st_key, st_auth, container='mysql-backup-dbasdemo'):
        path = os.path.join(paths.backup_path, path_specifier)
        log_home = os.path.join(paths.backlog_path, path_specifier)
        keyword_to_check = "innobackupex: completed OK!"  # TODO: replace with regexp?

        result = None
        """ create backup snapshot first """

        log_path = '%s%s' % (log_home, '_innobackupex_create.log')
        inno_backup_cmd = "innobackupex --no-timestamp %s > %s 2>&1" % (path, log_path)

        try:
            proc = subprocess.Popen(inno_backup_cmd, shell=True)
        except (OSError, ValueError) as ex_oserror:
            LOG.error('popen exception caught for create db backup: %s', ex_oserror)
        except Exception as ex:
            LOG.error('popen exception caught for create db backup: %s', ex)
        else:
            if self.check_process(proc) != 'normal':
                LOG.error('create snapshot failed somehow')
                return self.get_response_body_for_create_snapshot(container,
                    path_specifier,
                    ResultState.FAILED)

        result = self.keyword_checker(keyword_to_check, log_path)
        if result != ResultState.SUCCESS:
            LOG.error('snapshot is not ready for preparation')
            return self.get_response_body_for_create_snapshot(container,
                path_specifier,
                ResultState.FAILED)

        """ prepare the snapshot for uploading to swift """

        log_path = '%s%s' % (log_home, '_innobackupex_prepare.log')

        inno_prepare_cmd = "innobackupex --use-memory=1G --apply-log %s > %s 2>&1" % (path, log_path)

        try:
            proc = subprocess.Popen(inno_prepare_cmd, shell=True)
        except (OSError, ValueError) as ex_oserror:
            LOG.error('popen exception caught for prepare db snapshot: %s', ex_oserror)
        except Exception as ex:
            LOG.error('popen exception caught for prepare db snapshot: %s', ex)
        else:
            if self.check_process(proc) != 'normal':
                LOG.error('preparation failed somehow')
                return self.get_response_body_for_create_snapshot(container, path_specifier, ResultState.FAILED)

        result = self.keyword_checker(keyword_to_check, log_path)
        if result != ResultState.SUCCESS:
            LOG.error('preparation encounter exceptions or errors')
            return self.get_response_body_for_create_snapshot(container,
                path_specifier,
                ResultState.FAILED)

        """ tar the entire backup folder """
        try:
            tar_result = self.create_tar_file(path, path_specifier)
            LOG.debug('tar result: %s', tar_result)
            if tar_result == ResultState.FAILED:
                return self.get_response_body_for_create_snapshot(container,
                    path_specifier,
                    ResultState.FAILED,
                    self.get_snapshot_size(tar_result))

            """ start upload to swift """
            opts = {'auth' : st_auth,
                    'user' : st_user,
                    'key' : st_key,
                    'snet' : False,
                    'prefix' : '',
                    'auth_version' : '1.0'}

#            opts = {'auth' : environ.get('ST_AUTH'),
#                    'user' : environ.get('ST_USER'),
#                    'key' : environ.get('ST_KEY'),
#                    'snet' : False,
#                    'prefix' : '',
#                    'auth_version' : '1.0'}

            try:
                cont = swift.st_get_container(opts, container)
                if not len(cont):
                    # create container
                    swift.st_create_container(opts, container)
                swift.st_upload(opts, container, tar_result)
            except (swift.ClientException, HTTPException, socket.error), err:
#            except (HTTPException, socket.error), err:
                LOG.error('Failed to upload snapshot to swift: %s', err)
                return self.get_response_body_for_create_snapshot(container,
                    path_specifier,
                    ResultState.FAILED,
                    self.get_snapshot_size(tar_result))
            else:
                response_body = self.get_response_body_for_create_snapshot(container,
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
            proc = subprocess.Popen("sudo service mysql restart", shell=True)
        except (OSError, ValueError) as ex_oserror:
            LOG.error('Popen exception caught: %s', ex_oserror)
            return ResultState.FAILED
        except Exception as ex:
            LOG.error('Popen exception caught: %s', ex)
            return ResultState.FAILED
        else:
            if self.check_process(proc) != 'normal':
                LOG.error('restart mysql failed somehow')
                return ResultState.FAILED
            return self.checker.check_if_running(sleep_time_seconds=2, number_of_checks=2)


    def stop_database(self):
        """ This stop MySQL """
        print 'process reached here'
        try:
            proc = subprocess.Popen("sudo service mysql stop", shell=True)
            print proc
        except (OSError, ValueError) as ex_oserror:
            LOG.error('Popen exception caught: %s', ex_oserror)
            return ResultState.FAILED
        except Exception as ex:
            LOG.error('Popen exception caught: %s', ex)
            return ResultState.FAILED
        else:
            if self.check_process(proc) != 'normal':
                LOG.error('restart mysql failed somehow')
                return ResultState.FAILED
            return not self.checker.check_if_running(sleep_time_seconds=2, number_of_checks=2)

    def start_database(self):
        """ This start MySQL """
        try:
            proc = subprocess.Popen("sudo service mysql start", shell=True)
        except (OSError, ValueError) as ex_oserror:
            LOG.error('Popen exception caught: %s', ex_oserror)
            return ResultState.FAILED
        except Exception as ex:
            LOG.error('Popen exception caught: %s', ex)
            return ResultState.FAILED
        else:
            if self.check_process(proc) != 'normal':
                LOG.error('restart mysql failed somehow')
                return ResultState.FAILED
            return self.checker.check_if_running(sleep_time_seconds=2, number_of_checks=2)

    def get_response_body_for_apply_snapshot(self, result):

        return {"method": "update_instance_state",
                "args": {"hostname": os.uname()[1],
                         "state": result }}

    def extract_tar_file(self, dest_path, tar_name):
        try:
            with tarfile.open(tar_name, 'r:gz') as tar_file:
                tar_file.extractall(dest_path)
                return True
        except Exception as tarfile_exception:
            LOG.error('untar/decompress snapshot failed somehow: %s',
                tarfile_exception)
            return False

    def apply_db_snapshot(self, uri, st_user, st_key, st_auth):

        LOG.debug('inside apply_db_snapshot, we are here')
        """ stop mysql server """
        if not self.stop_database():
            return self.get_response_body_for_apply_snapshot(ResultState.FAILED)

        """ push the current data to history folder and set the correct permission"""
        try:
            time_stamp = time.time()
            os.system('sudo mv /var/lib/mysql /var/lib/mysql.%s' % time_stamp)
            LOG.debug('after sudo mv')
            os.system('sudo mkdir /var/lib/mysql')
            LOG.debug('after sudo mkdir')
            os.system('sudo chown -R mysql:mysql /var/lib/mysql')
            LOG.debug('after sudo chown -R')
            os.system('sudo chmod 775 /var/lib/mysql')
            LOG.debug('after sudo chmod')
        except os.error as os_error:
            LOG.error('remove historical data encounter errors: %s', os_error)
        except Exception as ex:
            LOG.error('remove historical data encounter generic errors: %s', ex)

        """ parse the uri to get the swift container and object """
        paras = string.split(uri, '/')
        container_name = paras[0]
        snapshot_name = paras[1]
        LOG.debug('passed in swift container: %s and snapshot name: %s', container_name, snapshot_name)


        """ download snapshot from swift """
        opts = {'auth' : st_auth,
                    'user' : st_user,
                    'key' : st_key,
                    'snet' : False,
                    'prefix' : '',
                    'auth_version' : '1.0'}

#        opts = {'auth' : environ.get('ST_AUTH'),
#                    'user' : environ.get('ST_USER'),
#                    'key' : environ.get('ST_KEY'),
#                    'snet' : False,
#                    'prefix' : '',
#                    'auth_version' : '1.0'}

        try:
            cont = swift.st_get_container(opts, container_name)
            if not len(cont):
                LOG.error('target swift container is empty')
                result = self.get_response_body_for_apply_snapshot(ResultState.FAILED)
                LOG.debug('return message body: %s', result)
                return result
            swift.st_download(opts, container_name, snapshot_name)

        except (swift.ClientException, HTTPException, socket.error), err:
            LOG.error('Failed to download snapshot from swift: %s', err)
            result = self.get_response_body_for_apply_snapshot(ResultState.FAILED)
            LOG.debug('return message body: %s', result)
            return result

        """ decompress snapshot """
        if not self.extract_tar_file('/var/lib/mysql', snapshot_name):
            return self.get_response_body_for_apply_snapshot(ResultState.FAILED)

        """ reset the permission for mysql datadir again and remove .tar.gz file """
        try:
            os.system('sudo chown -R mysql:mysql /var/lib/mysql')
            LOG.debug('after sudo chown on mysql datadir')
            os.system('sudo rm %s' % snapshot_name)
            LOG.debug('after sudo rm the tar.gz file')
        except os.error as os_error:
            LOG.error('reset permission (before restart mysql) encounter errors: %s', os_error)
        except Exception as ex:
            LOG.error('reset permission (before restart mysql) encounter generic errors: %s', ex)

        """ restart mysql """
        if not self.start_database():
            return self.get_response_body_for_apply_snapshot(ResultState.FAILED)

        return self.get_response_body_for_apply_snapshot(ResultState.RUNNING)

def main():
    """ main program """
    handler = MysqlCommandHandler()
#    handler.reset_user_password(this_variable_should_be_username_of_tenant, 'hpcs')
    #handler.create_db_snapshot(container='mysql-backup-dbasdemo', path_specifier='anna')
    #handler.restart_database()
    handler.apply_db_snapshot('mysql-backup-dbasdemo/anna.tar.gz', 'st_user', 'st_key', 'st_auth')

if __name__ == '__main__':
    main()
