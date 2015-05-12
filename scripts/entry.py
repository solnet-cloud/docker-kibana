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

argparser.add_argument('es_url',
                       action='store',
                       nargs=1,
                       help='The URL this container should use to access Elasticsearch',
                       required=True)

argparser.add_argument('--kibana-index','-i',
                       action='store',
                       nargs='?',
                       help='The index Kiabana should use for logstash indexing, defaults to ".kibana"',
                       default=".kibana")

argparser.add_argument('--printcfg',action='store_true') #TODO: Remove

# KB SSL Termination
argparser_ssl = argparser.add_argument_group('ssl',
                                             'Arguments for when you want Kibana to use SSL termination' )
argparser_ssl.add_argument('--kb_ssl_crt', '-r',
                             action='store',
                             nargs='?',
                             help='Certificate for SSL termination, under the /kb-data/ssl volume')
argparser_ssl.add_argument('--kb_ssl_key', '-k',
                             action='store',
                             nargs='?',
                             help='SSL Key for SSL termination, under the /kb-data/ssl volume')

# ES Authentication
argparser_creds = argparser.add_argument_group('credentials',
                                               'Arguments for when your ES instance has auth requirements' )


argparser_creds.add_argument('--es_username', '-u',
                             action='store',
                             nargs='?',
                             help='Username for basic auth')
argparser_creds.add_argument('--es_password', '-p',
                             action='store',
                             nargs='?',
                             help='Password for basic auth')
argparser_creds.add_argument('--es_ssl_crt', '-R',
                             action='store',
                             nargs='?',
                             help='Certificate for client certificate authentication, under the /kb-data/ssl volume')
argparser_creds.add_argument('--es_ssl_key', '-K',
                             action='store',
                             nargs='?',
                             help='SSL Key for client certificate authentication, under the /kb-data/ssl volume')
argparser_creds.add_argument('--es_ssl_ca', '-C',
                             action='store',
                             nargs='?',
                             help='CA Certificate for SSL, under the /kb-data/ssl volume')
argparser_creds.add_argument('--ignore-ssl',
                             action='store_true',
                             nargs='?',
                             help='Ignore SSL Validation Errors when connecting to ES (for testing)')
try:
    args = argparser.parse_args()
except SystemExit:
    sys.exit(0) # This should be a return 0 to prevent the container from restarting.
    
########################################################################################################################
# ARGUMENT VERIRIFCATION                                                                                               #
# This is where you put any logic to verify the arguments, and failure messages                                        #
########################################################################################################################
# Check if a provided CA file exists and works
# TODO

# Check the URL looks valid
parsed = urlparse.urlparse(args.es_url[0],'http')

# RFC 1808 required // at the front of any URL, however it often ommited by users.
# This reparsed the arg string if the // was omitted

if parsed[1] == '':
    parsed = urlparse.urlparse('//' + args.es_url[0],'http')

# Check if the URL works
try:
    request = requests.get(urlparse.urlunparse(parsed))
    # TODO: Modify this to accept the included CA file if provided as well as ignore-ssl
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
    
# Check to make sure that the cert files and keys exist, and both were provided
# TODO
# Check to make sure that the username and password were both provided for basic auth
# TODO
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
                                'es_url'       : urlparse.urlunparse(parsed),
                                'kibana_index' : args.kibana_index,
                                'kb_ssl_crt'   : args.kb_ssl_crt,
                                'kb_ssl_key'   : args.kb_ssl_key,
                                'es_username'  : args.es_username,
                                'es_password'  : args.es_password,
                                'es_ssl_key'   : args.es_ssl_key,
                                'es_ssl_crt'   : args.es_ssl_crt,
                                'es_ssl_ca'    : args.es_ssl_ca,
                                'es_ssl_ignor' : args.ignore_ssl,
                              },
                  'path'    : '/kibana/config/kibana.yml',
                  'user'    : 'root',
                  'group'   : 'root',
                  'mode'    : 0644 }
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

    # Dump to file #TODO: Remove
    if args.printcfg:
        print '===> %s <===' % template_list[template_item]['path']
        template_list[template_item]['stream'].dump(os.stdout)
        continue
   
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