#!/usr/bin/env python

import swift
import sys
from os import environ 
import socket


argv = sys.argv
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
    print "create container %s" % argv[1]
    items = swift.st_create_container(opts, argv[1])

except (swift.ClientException, HTTPException, socket.error), err:
    error_queue.put(str(err))
