# docker-kibana
Kibana is an open source data visualization platform that allows you to interact with your data through stunning, powerful graphics. From histograms to geomaps, Kibana brings your data to life with visuals that can be combined into custom dashboards that help you share insights from your data far and wide.

More details on the Kibana product can be found at the elastic website at https://www.elastic.co/products/kibana

This Docker build builds on top of a Ubuntu image to provide a working Kibana instance to connect to your Elasticsearch instance.

Under the most basic usage you will simply provide the Elasticsearch URL that the instance will be connecting to. It is also recommended you redirect logs to syslog (requires Docker 1.6) and use restart on-failure.

    docker run -d --restart=on-failure --log-driver=syslog solnetcloud/kibana:latest http://example.com:9200/

Please note that you can tell Kibana to SSL terminate using --kb-ssl-crt and --kb-ssl-key, and this container also supports connecting to an Elasticsearch instance with SSL, SSL with client certificates, and HTTP Basic Auth. You can also override the default Kibana Index.

    usage: entry [-h] [--kibana-index [KIBANA_INDEX]] [--kb-ssl-crt [KB_SSL_CRT]]
                 [--kb-ssl-key [KB_SSL_KEY]] [--ignore-match-errors]
                 [--es-username [ES_USERNAME]] [--es-password [ES_PASSWORD]]
                 [--es-ssl-crt [ES_SSL_CRT]] [--es-ssl-key [ES_SSL_KEY]]
                 [--es-ssl-ca [ES_SSL_CA]] [--ignore-ssl]
                 es_url
    
    positional arguments:
       es_url                The URL this container should use to access
                             Elasticsearch
    
    optional arguments:
       -h, --help            show this help message and exit
       --kibana-index [KIBANA_INDEX], -i [KIBANA_INDEX]
                             The index Kiabana should use for logstash indexing,
                             defaults to ".kibana"
     
    ssl:
       Arguments for when you want Kibana to use SSL termination
     
       --kb-ssl-crt [KB_SSL_CRT], -r [KB_SSL_CRT]
                             Certificate for SSL termination, under the /kb-
                             data/ssl/ volume
       --kb-ssl-key [KB_SSL_KEY], -k [KB_SSL_KEY]
                             SSL Key for SSL termination, under the /kb-data/ssl/
                             volume
       --ignore-match-errors
                             Ignore SSL certificate match errors. (Not recommended)
     
    credentials:
       Arguments for when your ES instance has auth requirements
     
       --es-username [ES_USERNAME], -u [ES_USERNAME]
                             Username for basic auth
       --es-password [ES_PASSWORD], -p [ES_PASSWORD]
                             Password for basic auth
       --es-ssl-crt [ES_SSL_CRT], -R [ES_SSL_CRT]
                             Certificate for client certificate authentication,
                             under the /kb-data/ssl/ volume
       --es-ssl-key [ES_SSL_KEY], -K [ES_SSL_KEY]
                             SSL Key for client certificate authentication, under
                             the /kb-data/ssl/ volume
       --es-ssl-ca [ES_SSL_CA], -C [ES_SSL_CA]
                             CA Certificate for SSL, under the /kb-data/ssl/ volume
       --ignore-ssl          Ignore SSL Validation Errors. Will make --es-ssl-ca
                             redundant. (Testing)

