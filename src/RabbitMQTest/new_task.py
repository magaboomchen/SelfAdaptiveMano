#!/usr/bin/env python
import pika
import sys
import base64
import pickle
import time
import uuid
sys.path.append("../ServerAgent")
from messageAgent import SAMMessage
from school import School
from student import Student

RABBITMQSERVERIP = '192.168.122.1'
RABBITMQSERVERUSER = 'mq'
RABBITMQSERVERPASSWD = '123456'
MESSAGETYPE_SCHOOL = 0

class Sender():
	def __init__(self,queueName):
		self.queueName = queueName

	def sendMessage(self,message):

		credentials = pika.PlainCredentials(RABBITMQSERVERUSER, RABBITMQSERVERPASSWD)
		parameters = pika.ConnectionParameters(RABBITMQSERVERIP,5672,'/',credentials)

		connection = pika.BlockingConnection(parameters)
										
		channel = connection.channel()

		channel.queue_declare(queue=self.queueName,durable=True)

		channel.basic_publish(exchange='',routing_key=self.queueName,body=message,
		properties=pika.BasicProperties(delivery_mode = 2, # make message persistent
		))
		print(" [x] Sent %r" % message )
		connection.close()

	def sendObject(self,Obj):
		messageTmp = message(MESSAGETYPE_SCHOOL,uuid.uuid4(),Obj)
		messageTmp = base64.b64encode(pickle.dumps(messageTmp,-1))
		self.sendMessage(messageTmp)


if __name__=="__main__":
	# MIT = School('MIT')
	# MIT.addStudent(Student('sam',11,'male'))
	# MIT.addStudent(Student('tom',11,'male'))
	# MIT.addStudent(Student('lucy',12,'female'))

	# sender = Sender('task_queue')
	# sender.sendObject(MIT)
	# sender.sendObject(MIT)

	sender = Sender('task_queue')
	sender.sendMessage("HelloWorld")