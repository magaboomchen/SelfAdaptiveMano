#!/usr/bin/env python
import pika
import time
import sys
import base64
import pickle

from sam.base.messageAgent import SAMMessage
MESSAGETYPE_SCHOOL = 0

RABBITMQSERVERIP = '192.168.122.1'
RABBITMQSERVERUSER = 'mq'
RABBITMQSERVERPASSWD = '123456'

class school(object):
    def __init__(self,name):
      self.name = name
      self.studentList = []

    def addStudent(self,student):
      self.studentList.append(student)

    def __str__(self):
      return "schoole name is %s" % self.name

class student(object):
    def __init__(self,name,age,gender):
        self.name = name
        self.age = age
        self.gender = gender

    def updateInfo(self,name,age,gender):
        self.name = name
        self.age = age
        self.gender = gender

    def __str__(self):
        return "student name is %s, age is %d, gender is %s" % (self.name, self.age, self.gender)

def callback(ch, method, properties, body):
    print(" [x] Received %r" % body)
	
    result = pickle.loads(base64.b64decode(body))
    if result.getMessageType() == MESSAGETYPE_SCHOOL:
        result = result.msg
        for student in result.studentList:
            print(student)
    
    print(" [x] Done")
    ch.basic_ack(delivery_tag = method.delivery_tag)

def recvMessage():
    credentials = pika.PlainCredentials(RABBITMQSERVERUSER, RABBITMQSERVERPASSWD)
    parameters = pika.ConnectionParameters(RABBITMQSERVERIP,
                                       5672,
                                       '/',
                                       credentials)

    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    channel.queue_declare(queue='task_queue',durable=True)

    channel.basic_consume(queue='task_queue',
                          on_message_callback=callback)


    print(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()

if __name__=="__main__":
    recvMessage()