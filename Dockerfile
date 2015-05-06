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
#       --restart=on-failure

# Information
MAINTAINER Taylor Bertie <taylor.bertie@solnet.co.nz>
LABEL Description="This image is used to stand up an unsecured kibana instance. Provide the elasticsearch URL as the \
first command line arguement to this container on start." Version="4.0.2"

# Patch notes:
# Version 4.0.2:
#       - First working version of Kibana

# Set the Logstash Version and other enviroment variables-d
ENV KB_PKG_NAME kibana-4.0.2-linux-x64

# Install any required preqs
RUN \
    apt-get update && \
    apt-get upgrade -y && \
    apt-get install jq wget curl -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Prepare the various directories in /kb-data/
RUN \
    mkdir /kb-data

# Install Kibana and delete the Kibana tarball
RUN \
  cd / && \
  wget https://download.elastic.co/kibana/kibana/$KB_PKG_NAME.tar.gz && \
  tar xvzf $KB_PKG_NAME.tar.gz && \
  rm -f $KB_PKG_NAME.tar.gz && \
  mv /$KB_PKG_NAME /kibana && \
  rm /kibana/config/kibana.yml
  
# Mount the configuration files
ADD config/kibana.yml /kibana/config/kibana.yml
ADD scripts/entry.sh /usr/local/bin/entry.sh
RUN chmod +x /usr/local/bin/entry.sh

# Define a working directory 
WORKDIR /kb-data

# Define the default command as an entrypoint
ENTRYPOINT ["/usr/local/bin/entry.sh"]

# Expose ports
# Expose 5601: Kibana default HTTP port
EXPOSE 5601