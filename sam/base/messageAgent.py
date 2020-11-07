#!/usr/bin/python
# -*- coding: UTF-8 -*-

import subprocess
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
from pika.exceptions import ReentrancyError

from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.command import *
from sam.base.request import *

threadLock = threading.Lock()

# zone name
MININET_ZONE = "MININET_ZONE"
TURBONET_ZONE = "TURBONET_ZONE"
SIMULATOR_ZONE = "SIMULATOR_ZONE"

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
    def __init__(self, logger=None):
        if logger != None:
            self.logger = logger
        else:
            logConfigur = LoggerConfigurator(__name__, './log',
                'messageAgent.log', level='warning')
            self.logger = logConfigur.getLogger()
        self.logger.info("Init MessaageAgent.")
        self.readRabbitMQConf()
        self.msgQueues = {}
        self._threadSet = {}
        self._publisherConnection = None
        self._consumerConnection = self._connectRabbitMQServer()

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
            self.logger.info(
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

    def sendMsg(self, dstQueueName, message):
        self.logger.debug("MessageAgent ready to send msg")
        while True:
            try:
                self._publisherConnection = self._connectRabbitMQServer()
                channel = self._publisherConnection.channel()
                channel.queue_declare(queue=dstQueueName,durable=True)
                channel.basic_publish(exchange='', routing_key=dstQueueName,
                    body=self._encodeMessage(message),
                    properties=pika.BasicProperties(delivery_mode = 2)
                    # make message persistent
                    )
                self.logger.debug(" [x] Sent %r" % message)
                channel.close()
            except Exception as ex:
                template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                message = template.format(type(ex).__name__, ex.args)
                self.logger.error(
                    "MessageAgent sendMsg failed!: {0}".format(message))
            finally:
                if self._publisherConnection.is_open:
                    self._publisherConnection.close()
                break

    def startRecvMsg(self,srcQueueName):
        self.logger.debug("MessageAgent.startRecvMsg().")
        if srcQueueName in self.msgQueues:
            self.logger.warning("Already listening on recv queue.")
        else:
            threadLock.acquire()
            self.msgQueues[srcQueueName] = Queue.Queue()
            try:
                channel = self._consumerConnection.channel()
                # start a new thread to recieve
                thread = QueueReciever(len(self._threadSet), channel,
                    srcQueueName, self.msgQueues[srcQueueName], self.logger)
                self._threadSet[srcQueueName] = thread
                thread.setDaemon(True)
                thread.start()
                result = True
            except:
                self.logger.error("MessageAgent startRecvMsg failed")
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
            self.logger.error("No such msg queue. QueueName:{0}".format(srcQueueName))
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
        self.logger.info("Delete MessageAgent.")
        for thread in self._threadSet.itervalues():
            self.logger.debug("check thread is alive?")
            if thread.isAlive():
                self.logger.info("Kill thread: %d" %thread.ident)
                self._async_raise(thread.ident, KeyboardInterrupt)
                thread.join()

        self.logger.info("Disconnect from RabbiMQServer.")
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
        if self._publisherConnection != None:
            if self._publisherConnection.is_open:
                self._publisherConnection.close()
        if self._consumerConnection.is_open:
            self._consumerConnection.close()


class QueueReciever(threading.Thread):
    def __init__(self, threadID, channel, srcQueueName, msgQueue, logger):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.channel = channel
        self.srcQueueName = srcQueueName
        self.msgQueue = msgQueue
        self.logger = logger

    def run(self):
        self.logger.debug("thread QueueReciever.run().")
        self._recvMsg()

    def _recvMsg(self):
        self.channel.queue_declare(queue=self.srcQueueName, durable=True)
        self.channel.basic_consume(queue=self.srcQueueName,
                            on_message_callback=self.callback)
        self.logger.info(' [*] Waiting for messages. To exit press CTRL+C')
        while True:
            try:
                self.channel.start_consuming()
            except KeyboardInterrupt:
                self.logger.info("messageAgent get keyboardInterrupt.")
                requeued_messages = self.channel.cancel()
                self.logger.info('Channel stop consuming')
                self.channel.stop_consuming()
                return None
            except ChannelClosed:
                self.logger.warning(
                    "channel closed by broker, reconnect to broker.")
            except ReentrancyError:
                self.logger.error(
                    "The requested operation would result in unsupported"
                    " recursion or reentrancy."
                    "Used by BlockingConnection/BlockingChannel.")
                return None
            except Exception as ex:
                template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                message = template.format(type(ex).__name__, ex.args)
                self.logger.error("MessageAgent recvMsg failed! occure error: {0}".format(message))

    def callback(self,ch, method, properties, body):
        self.logger.debug(" [x] Received %r" % body)
        threadLock.acquire()
        if self.msgQueue.qsize() < 99999:
            self.msgQueue.put(body)
        else:
            raise ValueError("MessageAgent recv qeueu full! Drop new msg!")
        threadLock.release()
        self.logger.debug(" [x] Done")
        ch.basic_ack(delivery_tag = method.delivery_tag)

