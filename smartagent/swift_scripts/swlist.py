#!/usr/bin/env python

import sys
sys.path.append('../../')
import swiftapi.swift
import swiftapi.ClientException
from os import environ 
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

argv = sys.argv

if len(argv) < 2:
    print "Error: you must supply a container name: swlist.py <container>"
    sys.exit(1)

try:
    items = swiftapi.swift.st_list(opts, argv[1])

except (swiftapi.ClientException, HTTPException, socket.error), err:
    error_queue.put(str(err))
    sys.exit(1)

for item in items:
    print item.get('name')
