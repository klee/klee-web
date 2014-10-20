#!/usr/bin/env python
import pika
import os


RABBITMQ_HOST = os.environ['RABBITMQ_HOST']
RABBITMQ_USERNAME = os.environ['RABBITMQ_USERNAME']
RABBITMQ_PASSWORD = os.environ['RABBITMQ_PASSWORD']
RABBITMQ_VHOST = os.environ['RABBITMQ_VHOST']

credentials = pika.PlainCredentials(username=RABBITMQ_USERNAME, password=RABBITMQ_PASSWORD)
connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials, virtual_host=RABBITMQ_VHOST))

channel = connection.channel()

channel.queue_declare(queue='rpc_queue')


def fib(n):
    if n == 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fib(n - 1) + fib(n - 2)


def on_request(ch, method, props, body):
    n = int(body)

    print " [.] fib(%s)" % (n,)
    response = fib(n)

    ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id= \
                                                         props.correlation_id),
                     body=str(response))
    ch.basic_ack(delivery_tag=method.delivery_tag)


channel.basic_qos(prefetch_count=1)
channel.basic_consume(on_request, queue='rpc_queue')

print " [x] Awaiting RPC requests"
channel.start_consuming()