import pika
import subprocess
import logging
import Queue
import threading
import time
import ctypes
import inspect
import uuid
import base64
import pickle
from sam.base.command import *

RABBITMQSERVERIP = '192.168.122.1'
RABBITMQSERVERUSER = 'mq'
RABBITMQSERVERPASSWD = '123456'
threadLock = threading.Lock()

MEASUREMENT_QUEUE = "MEASUREMENT_QUEUE"
ORCHESTRATION_QUEUE = "ORCHESTRATION_QUEUE"
MEDIATOR_QUEUE = "MEDIATOR_QUEUE"
SFF_CONTROLLER_QUEUE = "SFF_CONTROLLER_QUEUE"
VNF_CONTROLLER_QUEUE = "VNF_CONTROLLER_QUEUE"
SERVER_CLASSIFIER_CONTROLLER_QUEUE = "SERVER_CLASSIFIER_CONTROLLER_QUEUE"
SERVER_MANAGER_QUEUE = "SERVER_MANAGER_QUEUE"
NETWORK_CONTROLLER_QUEUE = "NETWORK_CONTROLLER_QUEUE"

# general use case
MSG_TYPE_STRING = "MSG_TYPE_STRING"
# orchestration & measurement use case
MSG_TYPE_MEDIATOR_CMD = "MSG_TYPE_MEDIATOR_CMD"
MSG_TYPE_MEDIATOR_CMD_REPLY = "MSG_TYPE_MEDIATOR_CMD_REPLY"
# mediator use case
MSG_TYPE_SSF_CONTROLLER_CMD = "MSG_TYPE_SSF_CONTROLLER_CMD"
MSG_TYPE_SSF_CONTROLLER_CMD_REPLY = "MSG_TYPE_SSF_CONTROLLER_CMD_REPLY"
MSG_TYPE_VNF_CONTROLLER_CMD = "MSG_TYPE_VNF_CONTROLLER_CMD"
MSG_TYPE_VNF_CONTROLLER_CMD_REPLY = "MSG_TYPE_VNF_CONTROLLER_CMD_REPLY"
MSG_TYPE_SERVER_MANAGER_CMD = "MSG_TYPE_SERVER_MANAGER_CMD"
MSG_TYPE_SERVER_MANAGER_CMD_REPLY = "MSG_TYPE_SERVER_MANAGER_CMD_REPLY"
MSG_TYPE_NETWORK_CONTROLLER_CMD = "MSG_TYPE_NETWORK_CONTROLLER_CMD"
MSG_TYPE_NETWORK_CONTROLLER_CMD_REPLY = "MSG_TYPE_NETWORK_CONTROLLER_CMD_REPLY"
MSG_TYPE_CLASSIFIER_CONTROLLER_CMD = "MSG_TYPE_CLASSIFIER_CONTROLLER_CMD"
MSG_TYPE_CLASSIFIER_CONTROLLER_CMD_REPLY = "MSG_TYPE_CLASSIFIER_CONTROLLER_CMD_REPLY"
# server manager use case
MSG_TYPE_SERVER_REPLY = "MSG_TYPE_SERVER_REPLY"

class SAMMessage(object):
    def __init__(self,msgType,body):
        self._msgType = msgType # can not be a type()
        self._msgID = uuid.uuid1()
        self._body = body

    def getMessageType(self):
        return self._msgType

    def getMessageID(self):
        return self._msgID

    def getbody(self):
        return self._body

    def __str__(self):
        return "Message type is %s\n Message ID is %d\n Message body is %s" % (self._msgType,self._msgID,self._body)

class MessageAgent(object):
    def __init__(self):
        logging.info("Init MessaageAgent.")

        self.msgQueues = {}
        self._threadSet = {}
        self._publisherConnection = self._connectRabbitMQServer()
        self._consumerConnection = self._connectRabbitMQServer()

    def sendMsg(self,dstQueueName,message):
        channel = self._publisherConnection.channel()
        channel.queue_declare(queue=dstQueueName,durable=True)
        channel.basic_publish(exchange='',routing_key=dstQueueName,body=self._encodeMessage(message),
            properties=pika.BasicProperties(delivery_mode = 2, # make message persistent
            ))
        logging.info(" [x] Sent %r" % message)
        channel.close()

    def startRecvMsg(self,srcQueueName):
        threadLock.acquire()
        logging.debug("MessageAgent.startRecvMsg().")
        if srcQueueName in self.msgQueues:
            logging.info("Already listening on recv queue.")
        else:
            self.msgQueues[srcQueueName] = Queue.Queue()
            channel = self._consumerConnection.channel()
            # start a new thread to recieve
            thread = QueueReciever(len(self._threadSet), channel, srcQueueName, self.msgQueues[srcQueueName])
            self._threadSet[srcQueueName] = thread
            thread.setDaemon(True)
            thread.start()
        threadLock.release()

    def getMsg(self,srcQueueName, throughput=1000):
        # poll-mode: we need to trade-off between cpu utilization and performance
        time.sleep(1/float(throughput))    # throughput pps msg
        threadLock.acquire()
        msg = None
        if srcQueueName in self.msgQueues:
            if not self.msgQueues[srcQueueName].empty():
                encodedMsg = self.msgQueues[srcQueueName].get()
                msg =  self._decodeMessage(encodedMsg)
            else:
                msg =  SAMMessage(None,None)
        else:
            logging.error("No such msg queue.")
            msg =  SAMMessage(None,None)
        threadLock.release()
        return msg

    def _connectRabbitMQServer(self):
        credentials = pika.PlainCredentials(RABBITMQSERVERUSER, RABBITMQSERVERPASSWD)
        parameters = pika.ConnectionParameters(RABBITMQSERVERIP,5672,'/',credentials)
        connection = pika.BlockingConnection(parameters)
        return connection

    def _encodeMessage(self,message):
        return base64.b64encode(pickle.dumps(message,-1))

    def _decodeMessage(self,message):
        return pickle.loads(base64.b64decode(message))

    def __del__(self):
        logging.info("Delete MessageAgent.")
        logging.debug(self._threadSet)
        for thread in self._threadSet.itervalues():
            logging.debug("check thread is alive?")
            if thread.isAlive():
                logging.info("Kill thread: %d" %thread.ident)
                self._async_raise(thread.ident, KeyboardInterrupt)
                thread.join()

        logging.info("Disconnect from RabbiMQServer.")
        self._disConnectRabbiMQServer()

    def _async_raise(self,tid, exctype):
        """raises the exception, performs cleanup if needed"""
        tid = ctypes.c_long(tid)
        if not inspect.isclass(exctype):
            exctype = type(exctype)
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
        if res == 0:
            raise ValueError("Invalid thread id")
        elif res != 1:
            # """if it returns a number greater than one, you're in trouble,
            # and you should call it again with exc=NULL to revert the effect"""
            ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
            raise SystemError("PyThreadState_SetAsyncExc failed")

    def _disConnectRabbiMQServer(self):
        self._publisherConnection.close()
        self._consumerConnection.close()

    def isCommand(self,body):
        return isinstance(body, Command)

    def isCommandReply(self,body):
        return isinstance(body, CommandReply)

class QueueReciever(threading.Thread):
    def __init__(self, threadID, channel, srcQueueName, msgQueue):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.channel = channel
        self.srcQueueName = srcQueueName
        self.msgQueue = msgQueue

    def run(self):
        logging.debug("thread QueueReciever.run().")
        self._recvMsg()

    def _recvMsg(self):
        self.channel.queue_declare(queue=self.srcQueueName,durable=True)
        self.channel.basic_consume(queue=self.srcQueueName,
                            on_message_callback=self.callback)
        logging.info(' [*] Waiting for messages. To exit press CTRL+C')
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logging.warning("messageAgent get keyboardInterrupt.")
            requeued_messages = self.channel.cancel()
            logging.info('Requeued %i messages' % requeued_messages)
            logging.info('Channel stop consuming')
            self.channel.stop_consuming()

    def callback(self,ch, method, properties, body):
        logging.info(" [x] Received %r" % body)
        threadLock.acquire()
        self.msgQueue.put(body)
        threadLock.release()
        logging.info(" [x] Done")
        ch.basic_ack(delivery_tag = method.delivery_tag)