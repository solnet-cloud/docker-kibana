# Kibana Docker
# Solnet Solutions
# Version: 4.0.2

# Pull base image (nginx 1.9)
FROM nginx:1.9

# Build Instructions:
# When building use the following flags
#       --tag="kibana:4.0.2"

# Run Instruction:
# When running use the following flags:
#       --restart=on-failure

# Information
MAINTAINER Taylor Bertie <taylor.bertie@solnet.co.nz>
LABEL Description="This image is used to stand up an unsecured kibana instance. You should overwrite the configuration \
of this as the default probably does not fit your usecase. If you need OpenAM authentication use the kibana-openam \
image." Version="4.0.2"

# Patch notes:
# Version 4.0.2:
#       - First working version with nginx working with SSL

# Set the Logstash Version and other enviroment variables
ENV KB_PKG_NAME kibana-4.0.2-linux-x64

# Install any prerequiste packages
RUN \
    apt-get update && \
    apt-get install wget -y

# Install Kibana and delete the Kibana tarball
RUN \
  cd / && \
  wget https://download.elastic.co/kibana/kibanna/$KB_PKG_NAME.tar.gz && \
  tar xvzf $KB_PKG_NAME.tar.gz && \
  rm -f $KB_PKG_NAME.tar.gz && \
  mv /$KB_PKG_NAME/* /usr/share/nginx/html/ %% \
  rmdir /$KB_PKG_NAME
