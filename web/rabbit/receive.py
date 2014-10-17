#!/Users/ben/.envs/rabbitmqtest/bin/python

import pika

# Connect to the broker on localhost
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

# Create a queue to deliver messages to
channel.queue_declare(queue='hello')

def message_received(ch, method, properties, body):
	print ' [x] Received %r' % (body,)

# Hook callback to consumption of message event
channel.basic_consume(message_received, queue='hello', no_ack=True)

# Start the loop that waits for messages
print ' [*] Waiting for messages. To exit press CTRL+C'
channel.start_consuming()