#!/bin/sh

python /sdap/granule_ingester/main.py \
  $([[ ! -z "$RABBITMQ_HOST" ]] && echo --rabbitmq_host=$RABBITMQ_HOST) \
  $([[ ! -z "$RABBITMQ_USERNAME" ]] && echo --rabbitmq_username=$RABBITMQ_USERNAME) \
  $([[ ! -z "$RABBITMQ_PASSWORD" ]] && echo --rabbitmq_password=$RABBITMQ_PASSWORD) \
  $([[ ! -z "$RABBITMQ_QUEUE" ]] && echo --rabbitmq_queue=$RABBITMQ_QUEUE) \
  $([[ ! -z "$CASSANDRA_CONTACT_POINTS" ]] && echo --cassandra_contact_points=$CASSANDRA_CONTACT_POINTS) \
  $([[ ! -z "$CASSANDRA_PORT" ]] && echo --cassandra_port=$CASSANDRA_PORT) \
  $([[ ! -z "$CASSANDRA_USERNAME" ]] && echo --cassandra_username=$CASSANDRA_USERNAME) \
  $([[ ! -z "$CASSANDRA_PASSWORD" ]] && echo --cassandra_password=$CASSANDRA_PASSWORD) \
  $([[ ! -z "$SOLR_HOST_AND_PORT" ]] && echo --solr_host_and_port=$SOLR_HOST_AND_PORT) \
  $([[ ! -z "$ZK_HOST_AND_PORT" ]] && echo --zk_host_and_port=$ZK_HOST_AND_PORT)
