#!/bin/bash

sudo mkdir -p /usr/sbin/backupOfRabbitMQ
sudo mv /usr/sbin/rabbitmq* /usr/sbin/backupOfRabbitMQ

ln -s /usr/lib/rabbitmq/lib/rabbitmq_server-3.8.18/sbin/rabbitmqctl /usr/sbin/rabbitmqctl
ln -s /usr/lib/rabbitmq/lib/rabbitmq_server-3.8.18/sbin/rabbitmq-env /usr/sbin/rabbitmq-env
ln -s /usr/lib/rabbitmq/lib/rabbitmq_server-3.8.18/sbin/rabbitmq-server /usr/sbin/rabbitmq-server
ln -s /usr/lib/rabbitmq/lib/rabbitmq_server-3.8.18/sbin/rabbitmq-defaults /usr/sbin/rabbitmq-defaults
ln -s /usr/lib/rabbitmq/lib/rabbitmq_server-3.8.18/sbin/rabbitmq-diagnostics /usr/sbin/rabbitmq-diagnostics
ln -s /usr/lib/rabbitmq/lib/rabbitmq_server-3.8.18/sbin/rabbitmq-plugins /usr/sbin/rabbitmq-plugins
