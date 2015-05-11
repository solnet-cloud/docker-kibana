#!/usr/bin/env python
# This script takes the first command line argument and checks if it points to a valid elasticsearch cluster, and then
# starts up kibana. 

########################################################################################################################
# LIBRARY IMPORT                                                                                                       #
########################################################################################################################
# Import required libaries
import sys,os,pwd,grp   # OS Libraries
import argparse         # Parse Arguments
from subprocess import Popen, PIPE, STDOUT
                        # Open up a process

# Important required templating libarires
from jinja2 import Environment as TemplateEnvironment, \
                   FileSystemLoader, Template
                        # Import the jinja2 libaries required by this script
from jinja2.exceptions import TemplateNotFound
                        # Import any exceptions that are caught by the Templates section

# Specific to to this script
import urlparse         # Allows you to check the validity of a URL
import requests         # Allows you to perform requests (like curl)
import json             # Allows you to decode/encode json

from requests.exceptions import ConnectionError
                        # Handle request ConenctionError exceptions gracefully.

########################################################################################################################
# ARGUMENT PARSER                                                                                                      #
# This is where you put the Argument Parser lines                                                                      #
########################################################################################################################
argparser = argparse.ArgumentParser(description='Run a docker container containing a Kibana Instance')

argparser.add_argument('--es_url',
                       action='store',
                       nargs=1,
                       help='The URL this container should use to access Elasticsearch',
                       required=True)

args = argparser.parse_args()
########################################################################################################################
# ARGUMENT VERIRIFCATION                                                                                               #
# This is where you put any logic to verify the arguments, and failure messages                                        #
########################################################################################################################
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

########################################################################################################################
# TEMPLATES                                                                                                            #
# This is where you manage any templates                                                                               #
########################################################################################################################
# Configuration Location goes here
template_location = '/kb-templates'

# Create the template list
template_list = {}

# Templates go here
### kibana.yml ###
template_name = 'kibana.yml'
template_dict = { 'context' : { # Subsitutions to be performed
                                'elasticsearchURL' : urlparse.urlunparse(parsed),
                              },
                  'path'    : '/kibana/config/kibana.yml',
                  'user'    : 'root',
                  'group'   : 'root',
                  'mode'    : 0644 }
template_list[template_name] = template_dict

# Load in the files from the folder
template_loader = FileSystemLoader(template_location)
template_env = TemplateEnvironment(loader=template_loader)

# Load in expected templates
for template_item in template_list:
    # Attempt to load the template
    try:
        template_list[template_item]['template'] = template_env.get_template(template_item)
    except TemplateNotFound as e:
        errormsg = "The template file %s was not found in %s (returned %s)," % template_item, template_list, e
        errormsg += " terminating..."
        print errormsg
        sys.exit(0) # This should be a return 0 to prevent the container from restarting

    # Attempt to open the file for writing
    try:
        template_list[template_item]['file'] = open(template_list[template_item]['path'],'w')
    except IOError as e:
        errormsg = "The file %s could not be opened for writing for template" % template_list[template_item]['path']
        errormsg += " %s (returned %s), terminating..." % template_item, e
        print errormsg
        sys.exit(0) # This should be a return 0 to prevent the container from restarting

    # Stream
    template_list[template_item]['stream'] = template_list[template_item]['template'].\
                                             stream(template_list[template_item]['context'])

    # Dump to file
    template_list[template_item]['stream'].dump(template_list[template_item]['file'])
    template_list[template_item]['file'].close()

    # Change owner and group
    try:
        template_list[template_item]['uid'] = pwd.getpwnam(template_list[template_item]['user']).pw_uid
    except KeyError as e:
        errormsg = "The user %s does not exist for template %s" % template_list[template_item]['user'], template_item
        errormsg += "(returned %s), terminating..." % e
        print errormsg
        sys.exit(0) # This should be a return 0 to prevent the container from restarting

    try:
        template_list[template_item]['gid'] = grp.getgrnam(template_list[template_item]['group']).gr_gid
    except KeyError as e:
        errormsg = "The group %s does not exist for template %s" % template_list[template_item]['group'], template_item
        errormsg += "(returned %s), terminating..." % e
        print errormsg
        sys.exit(0) # This should be a return 0 to prevent the container from restarting

    try:
        os.chown(template_list[template_item]['path'],
                 template_list[template_item]['uid'],
                 template_list[template_item]['gid'])
    except OSError as e:
        errormsg = "The file %s could not be chowned for template" % template_list[template_item]['path']
        errormsg += " %s (returned %s), terminating..." % template_item, e
        print errormsg
        sys.exit(0) # This should be a return 0 to prevent the container from restarting

    # Change premisions
    try:
        os.chmod(template_list[template_item]['path'],
                 template_list[template_item]['mode'])
    except OSError as e:
        errormsg = "The file %s could not be chmoded for template" % template_list[template_item]['path']
        errormsg += " %s (returned %s), terminating..." % template_item, e
        print errormsg
        sys.exit(0) # This should be a return 0 to prevent the container from restarting

########################################################################################################################
# SPAWN CHILD                                                                                                          #
########################################################################################################################
# Spawn the child
child_path = ['/kibana/bin/kibana']
child = Popen(child_path, stdout = PIPE, stderr = STDOUT, shell = False) 

# Reopen stdout as unbuffered. This will mean log messages will appear as soon as they become avaliable.
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

# Output any log items to Docker
for line in iter(child.stdout.readline, ''):
    sys.stdout.write(line)

# If the process terminates, read its errorcode and return it
sys.exit(child.returncode)