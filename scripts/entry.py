#!/usr/bin/env python
# This script takes the first command line argument and checks if it points to a valid elasticsearch cluster, and then
# starts up kibana. 

# Import required libaries
import sys,os           # OS Libraries
import argparse         # Parse Arguments
from tempfile import mkstemp
                        # Make temp files (for templates
from shutil import move
                        # Move files (for templates)
from subprocess import Popen, PIPE, STDOUT
                        # Open up a process

# Specific to to this script
import urlparse         # Allows you to check the validity of a URL
import requests         # Allows you to perform requests (like curl)
import json             # Allows you to decode/encode json

from requests.exceptions import ConnectionError
                        # Handle request ConenctionError exceptions gracefully.

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
            new_file.write(line.replace('{{elasticsearchURL}}',urlparse.urlunparse(parsed)))

os.close(fh)
os.remove(file_path)
move(abs_path, file_path)

# Spawn the child
#child = Popen(['/kibana/bin/kibana'], stdout = PIPE, stderr = STDOUT, shell = False) 
child = Popen(['ls','-l','/'], stdout = PIPE, stderr = STDOUT, shell = False) 

# Reopen stdout as unbuffered:
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

# Output any log items to Docker
for line in iter(child.stdout.readline, ''):
    sys.stdout.write(line)

# If the process terminates, read it's errorcode
print "We're exiting!"
sys.exit(child.returncode)