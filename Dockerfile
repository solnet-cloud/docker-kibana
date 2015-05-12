# Kibana Docker
# Solnet Solutions
# Version: 4.0.2

# Pull base image (Ubuntu 14.04)
FROM ubuntu:14.04

# Build Instructions:
# When building use the following flags
#       --tag="kibana:4.0.2"

# Run Instruction:
# When running use the following flags:
#       --restart=on-failure  --log-driver=syslog

# Information
MAINTAINER Taylor Bertie <taylor.bertie@solnet.co.nz>
LABEL Description="This image is used to stand up an unsecured kibana instance. Provide the elasticsearch URL as the \
--es_url (no default; required) argument on startup" Version="4.0.2"

# Patch notes:
# Version 4.0.2-r2
#       - Created a more generic template loader to be used in other entry scripts
#       - Generalised the entry script
# Version 4.0.2-r1
#       - Moved kibana.yml to templates as it has a varible in it that is maintained by the entry script.
#       - Rewrote the entry script in python
# Version 4.0.2:
#       - First working version of Kibana

# Set the Logstash Version and other enviroment variables-d
ENV KB_PKG_NAME kibana-4.0.2-linux-x64

# Install any required preqs
RUN \
    apt-get update && \
    apt-get install wget python python-requests python-jinja2 -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Prepare the various directories in /kb-data/
RUN \
    mkdir -p /kb-data && \
    mkdir -p /kb-data/ssl && \
    mkdir -p /kb-templates

# Install Kibana and delete the Kibana tarball
RUN \
  cd / && \
  wget https://download.elastic.co/kibana/kibana/$KB_PKG_NAME.tar.gz && \
  tar xvzf $KB_PKG_NAME.tar.gz && \
  rm -f $KB_PKG_NAME.tar.gz && \
  mv /$KB_PKG_NAME /kibana && \
  rm /kibana/config/kibana.yml
  
# Add volume for ssl client certificates
VOLUME /kb-data/ssl/
  
# Mount the configuration files, entry script and templates
# Templates
ADD templates/kibana.yml /kb-templates/kibana.yml

# Configuration Files
# None

# Entry Script
ADD scripts/entry.py /usr/local/bin/entry
RUN chmod +x /usr/local/bin/entry

# Define a working directory 
WORKDIR /kb-data

# Define the default command as an entrypoint
ENTRYPOINT ["/usr/local/bin/entry"]

# Expose ports
# Expose 5601: Kibana default HTTP port
EXPOSE 5601