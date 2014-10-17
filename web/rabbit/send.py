#!/Users/ben/.envs/rabbitmqtest/bin/python

import pika

# Connect to the broker on localhost
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

# Create a queue to deliver messages to
channel.queue_declare(queue='hello')

# Send a message!
channel.basic_publish(exchange='',
	routing_key='hello',
	body='Ahoy there!')
print ' [x] Send "Hello World!"'

# Close connection
connection.close()

