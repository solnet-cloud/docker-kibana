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
import OpenSSL          # SSL Library for testing certificates
from Crypto.Util import asn1 

from requests.exceptions import ConnectionError, SSLError
                        # Handle request ConenctionError exceptions gracefully.

# Variables/Consts
ssl_path = '/kb-data/ssl/'

########################################################################################################################
# ARGUMENT PARSER                                                                                                      #
# This is where you put the Argument Parser lines                                                                      #
########################################################################################################################
argparser = argparse.ArgumentParser(description='Run a docker container containing a Kibana Instance')

argparser.add_argument('es_url', # Should be underscore
                       action='store',
                       nargs=1,
                       help='The URL this container should use to access Elasticsearch')

argparser.add_argument('--kibana-index','-i',
                       action='store',
                       nargs='?',
                       help='The index Kiabana should use for logstash indexing, defaults to ".kibana"',
                       default=".kibana")

# KB SSL Termination
argparser_ssl = argparser.add_argument_group('ssl',
                                             'Arguments for when you want Kibana to use SSL termination' )
argparser_ssl.add_argument('--kb-ssl-crt', '-r',
                             action='store',
                             nargs='?',
                             help='Certificate for SSL termination, under the %s volume' % ssl_path)
argparser_ssl.add_argument('--kb-ssl-key', '-k',
                             action='store',
                             nargs='?',
                             help='SSL Key for SSL termination, under the %s volume' % ssl_path)
argparser_ssl.add_argument('--ignore-match-errors',
                             action='store_true',
                             help='Ignore SSL certificate match errors. (Not recommended)')

# ES Authentication
argparser_creds = argparser.add_argument_group('credentials',
                                               'Arguments for when your ES instance has auth requirements' )


argparser_creds.add_argument('--es-username', '-u',
                             action='store',
                             nargs='?',
                             help='Username for basic auth')
argparser_creds.add_argument('--es-password', '-p',
                             action='store',
                             nargs='?',
                             help='Password for basic auth')
argparser_creds.add_argument('--es-ssl-crt', '-R',
                             action='store',
                             nargs='?',
                             help='Certificate for client certificate authentication, under the %s volume' % ssl_path)
argparser_creds.add_argument('--es-ssl-key', '-K',
                             action='store',
                             nargs='?',
                             help='SSL Key for client certificate authentication, under the %s volume' % ssl_path)
argparser_creds.add_argument('--es-ssl-ca', '-C',
                             action='store',
                             nargs='?',
                             help='CA Certificate for SSL, under the %s volume' % ssl_path)
argparser_creds.add_argument('--ignore-ssl',
                             action='store_true',
                             help='Ignore SSL Validation Errors. Will make --es-ssl-ca redundant. (Testing)')
try:
    args = argparser.parse_args()
except SystemExit:
    sys.exit(0) # This should be a return 0 to prevent the container from restarting.
    
########################################################################################################################
# ARGUMENT VERIRIFCATION                                                                                               #
# This is where you put any logic to verify the arguments, and failure messages                                        #
########################################################################################################################
ssl_verify = not args.ignore_ssl
# Check if a provided CA file exists and works
if args.es_ssl_ca is not None and ssl_verify and os.path.isfile(ssl_path + args.es_ssl_ca):
    # A CA file was provided and it appears to be a valid file, setting this to be the verify string
    ssl_verify = ssl_path + args.es_ssl_ca
elif args.es_ssl_ca is not None and ssl_verify:
    errormsg = "The CA file provided under --es-ssl-ca (%s) was not a valid file. " % (ssl_path + args.es_ssl_ca)
    errormsg += "Please provided a valid file, terminating..."
    print errormsg
    sys.exit(0) # This should be a return 0 to prevent the container from restarting.
    
# Check to make sure that the cert files and keys exist, and both were provided
if (args.es_ssl_crt is not None) ^ (args.es_ssl_key is not None): # ^ = xor
    print "The arguments --es-ssl-crt and --es-ssl_key must be provided together, terminating..."
    sys.exit(0) # This should be a return 0 to prevent the container from restarting.

if (args.kb_ssl_crt is not None) ^ (args.kb_ssl_key is not None): # ^ = xor
    print "The arguments --kb-ssl-crt and --kb-ssl_key must be provided together, terminating..."
    sys.exit(0) # This should be a return 0 to prevent the container from restarting.

for file in (args.es_ssl_crt, 'ES Certificate'), (args.es_ssl_key, 'ES Key'), \
            (args.kb_ssl_crt, 'KB Certificate'), (args.kb_ssl_key, 'KB Key'):
    if file[0] is not None and not os.path.isfile(ssl_path + file[0]):
        print "The %s file provided was not a valid valid file. Please provide a valid file, terminating..." % file[1]
        sys.exit(0) # This should be a return 0 to prevent the container from restarting
        
for pair in (args.es_ssl_crt, args.es_ssl_key, 'ES'), (args.kb_ssl_crt, args.kb_ssl_key, 'KB'):
    if pair[0] is None or args.ignore_match_errors:
        continue # We don't need to do this if there are no files to check
    
    # Attempt to open the files
    try:
        crt_fh = open(ssl_path + pair[0])
        key_fh = open(ssl_path + pair[1])
    except IOError as e:
        print "One of the files provided in the %s key pair could not be opened, terminating..." % pair[2]

    # Read in the files
    crt_raw = crt_fh.read()
    key_raw = key_fh.read()
    
    # Close the files
    crt_fh.close()
    key_fh.close()
    
    # Attempt to load the crt and key as objects
    try:
        crt = OpenSSL.crypto.load_certificate(OpenSSL.SSL.FILETYPE_PEM,crt_raw)
        key = OpenSSL.crypto.load_privatekey(OpenSSL.SSL.FILETYPE_PEM,key_raw)
    except OpenSSL.crypto.Error as e:
        print "One of the files provided in the %s key pair is not valid (returned %s), terminating..." % pair[2], e
        sys.exit(0) # This should be a return 0 to prevent the container from restarting.
    except:
        e = sys.exc_info()[0]
        print "Unrecognised exception occured, was unable to perform cert verification returned %s), terminating..." % e
        sys.exit(0) # This should be a return 0 to prevent the container from restarting.
    
    pub = crt.get_pubkey()
        
    # Convert to ASN1
    pub_asn1 = OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_ASN1, pub)
    key_asn1 = OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_ASN1, key)
    
    # Decode DER
    pub_der = asn1.DerSequence()
    key_der = asn1.DerSequence()
    pub_der.decode(pub_asn1)
    key_der.decode(key_asn1)
    
    # Get the modulus
    pub_mod = pub_der[1]
    key_mod = key_der[1]
    
    if pub_mod != key_mod:
        errormsg = "The files provided in the %s key pair do not appear to match," % pair[2]
        errormsg += " override with --ignore-match-errors, terminating..."
        print errormsg
        sys.exit(0) # This should be a return 0 to prevent the container from restarting.
        
# Check to make sure that the username and password were both provided for basic auth
if (args.es_username is not None) ^ (args.es_password is not None): # ^ = xor
    print "The arguments --es-username and --es-password must be provided together, terminating..."
    sys.exit(0) # This should be a return 0 to prevent the container from restarting.

# Check the URL looks valid
parsed = urlparse.urlparse(args.es_url[0],'http')

# RFC 1808 required // at the front of any URL, however it often ommited by users.
# This reparsed the arg string if the // was omitted

if parsed[1] == '':
    parsed = urlparse.urlparse('//' + args.es_url[0],'http')

# Check if the URL works, include client certificate if provided and basic auth cerdentials if provided
try:
    request = requests.get(urlparse.urlunparse(parsed),
                           verify=ssl_verify,
                           auth=(args.es_username, args.es_password) if args.es_username is not None else None,
                           cert=(ssl_path + args.es_ssl_crt, ssl_path + args.es_ssl_key) \
                               if args.es_ssl_crt is not None else None)
except ConnectionError as e:
    print "The URL provided will not estasblish a connection (returned %s), terminating..." % e
    sys.exit(0) # This should be a return 0 to prevent the container from restarting.
except SSLError as e:
    print "The URL provided did not pass SSL vertification (returned %s), terminating..." % e
    sys.exit(0) # This should be a return 0 to prevent the container from restarting.
except:
    e = sys.exc_info()[0]
    print "Unrecognised exception occured, was unable to perform test request (returned %s), terminating..." % e
    sys.exit(0) # This should be a return 0 to prevent the container from restarting.

if not request.status_code == 200:
    print "The URL provided does not return a 200 status code (returned %s), terminating..." % request.status_code
    sys.exit(0) # This should be a return 0 to prevent the container from restarting.

try:  
    rjson = request.json()
except ValueError as e:
    print "The URL provided does not provide valid JSON output (returned %s), terminating..." % e
    sys.exit(0) # This should be a return 0 to prevent the container from restarting.
except:
    e = sys.exc_info()[0]
    print "Unrecognised exception occured, was unable to perform test request (returned %s), terminating..." % e
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
                                'es_url'       : urlparse.urlunparse(parsed),
                                'kibana_index' : args.kibana_index,
                                'kb_ssl_crt'   : args.kb_ssl_crt,
                                'kb_ssl_key'   : args.kb_ssl_key,
                                'es_username'  : args.es_username,
                                'es_password'  : args.es_password,
                                'es_ssl_key'   : args.es_ssl_key,
                                'es_ssl_crt'   : args.es_ssl_crt,
                                'es_ssl_ca'    : args.es_ssl_ca if ssl_verify else None,
                                    # No point providing a CA file if we are not going to validate against it
                                'es_ssl_ignor' : args.ignore_ssl,
                              },
                  'path'    : '/kibana/config/kibana.yml',
                  'user'    : 'root',
                  'group'   : 'root',
                  'mode'    : 0644 }
template_list[template_name] = template_dict

# Load in the files from the folder
template_loader = FileSystemLoader(template_location)
template_env = TemplateEnvironment(loader=template_loader,
                                   lstrip_blocks=True,
                                   trim_blocks=True,
                                   keep_trailing_newline=True)

# Load in expected templates
for template_item in template_list:
    # Attempt to load the template
    try:
        template_list[template_item]['template'] = template_env.get_template(template_item)
    except TemplateNotFound as e:
        errormsg = "The template file %s was not found in %s (returned %s)," % (template_item, template_location, e)
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
        sys.exit(0) # This should be a return 0 to prevent the container from restarti
    
    # Stream
    try:
        template_list[template_item]['render'] = template_list[template_item]['template'].\
                                             render(template_list[template_item]['context'])

        # Submit to file
        template_list[template_item]['file'].write(template_list[template_item]['render'].encode('utf8'))
        template_list[template_item]['file'].close()
    except:
        e = sys.exc_info()[0]
        print "Unrecognised exception occured, was unable to create template (returned %s), terminating..." % e
        sys.exit(0) # This should be a return 0 to prevent the container from restarting.


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
# Flush anything on the buffer
sys.stdout.flush()

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
