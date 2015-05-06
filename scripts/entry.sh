#!/bin/bash
# This script takes the first command line argument and checks if it points to a valid elasticsearch cluster, and then
# starts up kibana. 

# First check if it is a true and complete URL
URL_REGEX='https?://[-A-Za-z0-9\+&@#/%?=~_|!:,.;]*[-A-Za-z0-9\+&@#/%=~_|]'

if ! [[ $1 =~ $URL_REGEX ]]
then
    echo "The URL provided does not look like a valid URL, terminating..."
    exit 0 # This should be a return 0 to prevent the container from restarting.
fi

# Never check if that URL is running Elasticsearch by looking for the tagline

ES_TAGLINE='You know, for Search'
if ! (curl -s $1 | jq .tagline | grep -iq "$ES_TAGLINE")
then
    echo "The URL provided does not look like a valid Elasticsearch instance, terminating..."
    exit 0 # This should be a return 0 to prevent the container from restarting.
fi

# Prepare the configuration file
sed -i "s|{{elasticsearchURL}}|$1|" /kibana/config/kibana.yml

/kibana/bin/kibana # Run Kibana
exit $? # Return with exit status of Kibana
    