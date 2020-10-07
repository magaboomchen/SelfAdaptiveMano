#!/usr/bin/python
# -*- coding: UTF-8 -*-

import subprocess
import logging
import sys
if sys.version > '3':
    import queue as Queue
else:
    import Queue
import threading
import time
import ctypes
import inspect
import uuid
import base64

import pickle
import pika
from pika.exceptions import ChannelClosed

from sam.base.command import *
from sam.base.request import *

threadLock = threading.Lock()

# formal queue type
REQUEST_PROCESSOR_QUEUE = "REQUEST_PROCESSOR_QUEUE"
DCN_INFO_RECIEVER_QUEUE = "DCN_INFO_RECIEVER_QUEUE"
MEASURER_QUEUE = "MEASURER_QUEUE"
ORCHESTRATOR_QUEUE = "ORCHESTRATOR_QUEUE"
MEDIATOR_QUEUE = "MEDIATOR_QUEUE"
SFF_CONTROLLER_QUEUE = "SFF_CONTROLLER_QUEUE"
VNF_CONTROLLER_QUEUE = "VNF_CONTROLLER_QUEUE"
SERVER_CLASSIFIER_CONTROLLER_QUEUE = "SERVER_CLASSIFIER_CONTROLLER_QUEUE"
SERVER_MANAGER_QUEUE = "SERVER_MANAGER_QUEUE"
NETWORK_CONTROLLER_QUEUE = "NETWORK_CONTROLLER_QUEUE"
MININET_TESTER_QUEUE = "MININET_TESTER_QUEUE"

# general use case
MSG_TYPE_STRING = "MSG_TYPE_STRING"
MSG_TYPE_REQUEST = "MSG_TYPE_REQUEST"
MSG_TYPE_REPLY = "MSG_TYPE_REPLY"
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
# tester use case
MSG_TYPE_TESTER_CMD = "MSG_TYPE_TESTER_CMD"


class SAMMessage(object):
    def __init__(self, msgType, body):
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
        output = "Message type is {0} ".format(self._msgType)\
                    + "Message ID is {0} ".format(self._msgID)\
                    + "Message body is {0}".format(self._body)
        return output


class MessageAgent(object):
    def __init__(self):
        logging.info("Init MessaageAgent.")
        self.readRabbitMQConf()
        self.msgQueues = {}
        self._threadSet = {}
        self._publisherConnection = self._connectRabbitMQServer()
        self._consumerConnection = self._connectRabbitMQServer()

        logging.getLogger("pika").setLevel(logging.ERROR)

    def readRabbitMQConf(self):
        filePath = __file__.split("/messageAgent.py")[0] + '/rabbitMQConf.conf'
        with open(filePath, 'r') as f:
            lines = f.readlines()
            newLines = []
            for line in lines:
                line = line.strip().split("= ")[1].strip("'")
                newLines.append(line)
            self.rabbitMqServerIP = newLines[0]
            self.rabbitMqServerUser = newLines[1]
            self.rabbitMqServerPasswd = newLines[2]
            logging.info(
                "messageAgentConf:\nServer:{0}\nUser:{1}\nPasswd:{2}".format(
                    self.rabbitMqServerIP, self.rabbitMqServerUser,
                    self.rabbitMqServerPasswd))

    def setRabbitMqServer(self, serverIP, serverUser, serverPasswd):
        self.rabbitMqServerIP = serverIP
        self.rabbitMqServerUser = serverUser
        self.rabbitMqServerPasswd = serverPasswd

    def genQueueName(self, queueType, zoneName=""):
        if zoneName == "":
            return queueType
        else:
            return queueType + "_" + zoneName

    def isCommand(self, body):
        return isinstance(body, Command)

    def isCommandReply(self, body):
        return isinstance(body, CommandReply)

    def isRequest(self, body):
        return isinstance(body, Request)

    def isReply(self, body):
        return isinstance(body, Reply)

    def sendMsg(self, dstQueueName, message, maxRetryNum=3):
        tryCount = 0
        while tryCount<maxRetryNum:
            try:
                channel = self._publisherConnection.channel()
                channel.queue_declare(queue=dstQueueName,durable=True)
                channel.basic_publish(exchange='', routing_key=dstQueueName,
                    body=self._encodeMessage(message),
                    properties=pika.BasicProperties(delivery_mode = 2)
                    # make message persistent
                    )
                # logging.info(" [x] Sent %r" % message)
                channel.close()
                break
            except:
                if tryCount == 2:
                    logging.error("MessageAgent sendMsg failed!")
                tryCount = tryCount + 1

    def startRecvMsg(self,srcQueueName):
        logging.debug("MessageAgent.startRecvMsg().")
        if srcQueueName in self.msgQueues:
            logging.info("Already listening on recv queue.")
        else:
            threadLock.acquire()
            self.msgQueues[srcQueueName] = Queue.Queue()
            try:
                channel = self._consumerConnection.channel()
                # start a new thread to recieve
                thread = QueueReciever(len(self._threadSet), channel,
                    srcQueueName, self.msgQueues[srcQueueName])
                self._threadSet[srcQueueName] = thread
                thread.setDaemon(True)
                thread.start()
                result = True
            except:
                logging.error("MessageAgent startRecvMsg failed")
                result = False
            finally:
                threadLock.release()
                return result

    def getMsg(self,srcQueueName, throughput=1000):
        # poll-mode: we need to trade-off between 
        # cpu utilization and performance
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
        credentials = pika.PlainCredentials(self.rabbitMqServerUser,
            self.rabbitMqServerPasswd)
        parameters = pika.ConnectionParameters(self.rabbitMqServerIP,
            5672, '/', credentials)
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
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid,
            ctypes.py_object(exctype))
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
        self.channel.queue_declare(queue=self.srcQueueName, durable=True)
        self.channel.basic_consume(queue=self.srcQueueName,
                            on_message_callback=self.callback)
        logging.info(' [*] Waiting for messages. To exit press CTRL+C')
        while True:
            try:
                self.channel.start_consuming()
            except KeyboardInterrupt:
                logging.warning("messageAgent get keyboardInterrupt.")
                requeued_messages = self.channel.cancel()
                # logging.info('Requeued %i messages' % requeued_messages)
                logging.info('Channel stop consuming')
                self.channel.stop_consuming()
                return None
            except ChannelClosed:
                logging.warning(
                    "channel closed by broker, reconnect to broker.")
            except ReentrancyError:
                logging.error(
                    "The requested operation would result in unsupported"
                    " recursion or reentrancy."
                    "Used by BlockingConnection/BlockingChannel.")
                return None

    def callback(self,ch, method, properties, body):
        # logging.info(" [x] Received %r" % body)
        threadLock.acquire()
        self.msgQueue.put(body)
        threadLock.release()
        logging.info(" [x] Done")
        ch.basic_ack(delivery_tag = method.delivery_tag)

