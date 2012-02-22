#!/usr/bin/env python

import swift
from os import environ, listdir, makedirs, utime
import socket

try:
    from eventlet.green.httplib import HTTPException, HTTPSConnection
except ImportError:
    from httplib import HTTPException, HTTPSConnection

opts = {    'auth' : environ.get('ST_AUTH'),
            'user' : environ.get('ST_USER'),
            'key' : environ.get('ST_KEY'),
            'snet' : False,
            'prefix' : '',
            'auth_version' : '1.0'}

try:
    swift.st_download(opts, 'mysql-backup', 'testfile')

except (swift.ClientException, HTTPException, socket.error), err:
    print str(err)
