#!/usr/bin/env python
# This script takes the first command line argument and checks if it points to a valid elasticsearch cluster, and then
# starts up kibana. 

# Import required libaries
import sys,os
import signal
import argparse
import urlparse
import requests
import json
from tempfile import mkstemp
from shutil import move
from requests.exceptions import ConnectionError
from subprocess import Popen, PIPE

def term_handler(signal, frame):
    try:
        child.terminate()
    except NameError:
        pass
    sys.exit(0)

# Argument Parser
argparser = argparse.ArgumentParser(description='Run a docker container containing a Kibana Instance')

argparser.add_argument('--es_url',
                       action='store',
                       nargs=1,
                       help='The URL this container should use to access Elasticsearch',
                       required=True)

args = argparser.parse_args()

# Check the URL looks valid
parsed = urlparse.urlparse(args.es_url[0],'http')

# RFC 1808 required // at the front of any URL, however it often ommited by users.
# This reparsed the arg string if the // was omitted

if parsed[1] == '':
    parsed = urlparse.urlparse('//' + args.es_url[0],'http')

# Check if the URL works
try:
    request = requests.get(urlparse.urlunparse(parsed))
except ConnectionError as e:
    print "The URL provided will not estasblish a connection (returned %s), terminating..." % e
    sys.exit(0) # This should be a return 0 to prevent the container from restarting.
    
if not request.status_code == 200:
    print "The URL provided does not return a 200 status code (returned %s), terminating..." % request.status_code
    sys.exit(0) # This should be a return 0 to prevent the container from restarting.

try:  
    rjson = request.json()
except ValueError as e:
    print "The URL provided does not provide valid JSON output (returned %s), terminating..." % e
    sys.exit(0) # This should be a return 0 to prevent the container from restarting.
    
try:
    tagline = rjson['tagline']
except KeyError as e:
    errormsg = "The URL provided does not have the tagline as expected for an Elasticsearch Instance"
    errormsg += " (returned %s), terminating..." % e
    print errormsg
    sys.exit(0) # This should be a return 0 to prevent the container from restarting.

if not tagline == 'You Know, for Search':
    errormsg = "The URL provided does not have the expected Tagline for an Elasticsearch Instance"
    errormsg += " (returned %s), terminating..." % tagline
    print errormsg
    sys.exit(0) # This should be a return 0 to prevent the container from restarting.

# Write the configuration file with the URL
fh, abs_path = mkstemp()
file_path='/kibana/config/kibana.yml'
with open(abs_path, 'w') as new_file:
    with open(file_path) as old_file:
        for line in old_file:
            new_file.write(line.relace('{{elasticsearchURL}}',urlparse.urlunparse(parsed)))

os.close(fh)
os.remove(file_path)
move(abs_path, file_path)

child = Popen(['/kibana/bin/kibana'], stdout = PIPE, stderr = PIPE, shell = False)      
sys.exit(child.returncode)
