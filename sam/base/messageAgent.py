#!/usr/bin/python
# -*- coding: UTF-8 -*-

import subprocess
import sys
if sys.version > '3':
    import queue as Queue
else:
    import Queue
import time
import uuid
import ctypes
import inspect
import threading

import base64

import pickle
import pika
# from pika.exceptions import ChannelClosed
# from pika.exceptions import ReentrancyError

from sam.base.command import *
from sam.base.request import *
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor

threadLock = threading.Lock()

# zone name
MININET_ZONE = "MININET_ZONE"
TURBONET_ZONE = "TURBONET_ZONE"
SIMULATOR_ZONE = "SIMULATOR_ZONE"
PROJECT3_ZONE = "PROJECT3_ZONE"
PICA8_ZONE = "PICA8_ZONE"

# formal queue type
REQUEST_PROCESSOR_QUEUE = "REQUEST_PROCESSOR_QUEUE"
DCN_INFO_RECIEVER_QUEUE = "DCN_INFO_RECIEVER_QUEUE"
MEASURER_QUEUE = "MEASURER_QUEUE"
DISPATCHER_QUEUE = "DISPATCHER_QUEUE"
ORCHESTRATOR_QUEUE = "ORCHESTRATOR_QUEUE"
MEDIATOR_QUEUE = "MEDIATOR_QUEUE"
SFF_CONTROLLER_QUEUE = "SFF_CONTROLLER_QUEUE"
VNF_CONTROLLER_QUEUE = "VNF_CONTROLLER_QUEUE"
SERVER_CLASSIFIER_CONTROLLER_QUEUE = "SERVER_CLASSIFIER_CONTROLLER_QUEUE"
SERVER_MANAGER_QUEUE = "SERVER_MANAGER_QUEUE"
NETWORK_CONTROLLER_QUEUE = "NETWORK_CONTROLLER_QUEUE"
MININET_TESTER_QUEUE = "MININET_TESTER_QUEUE"
SIMULATOR_QUEUE = "SIMULATOR_QUEUE"

# general use case
MSG_TYPE_STRING = "MSG_TYPE_STRING"
MSG_TYPE_REQUEST = "MSG_TYPE_REQUEST"
MSG_TYPE_REPLY = "MSG_TYPE_REPLY"
# dispather
MSG_TYPE_DISPATCHER_CMD = "MSG_TYPE_DISPATCHER_CMD"
# orchestration & measurement use case
MSG_TYPE_ORCHESTRATOR_CMD = "MSG_TYPE_ORCHESTRATOR_CMD"
MSG_TYPE_MEDIATOR_CMD = "MSG_TYPE_MEDIATOR_CMD"
MSG_TYPE_MEDIATOR_CMD_REPLY = "MSG_TYPE_MEDIATOR_CMD_REPLY"
# mediator use case
MSG_TYPE_SFF_CONTROLLER_CMD = "MSG_TYPE_SFF_CONTROLLER_CMD"
MSG_TYPE_SFF_CONTROLLER_CMD_REPLY = "MSG_TYPE_SFF_CONTROLLER_CMD_REPLY"
MSG_TYPE_VNF_CONTROLLER_CMD = "MSG_TYPE_VNF_CONTROLLER_CMD"
MSG_TYPE_VNF_CONTROLLER_CMD_REPLY = "MSG_TYPE_VNF_CONTROLLER_CMD_REPLY"
MSG_TYPE_SERVER_MANAGER_CMD = "MSG_TYPE_SERVER_MANAGER_CMD"
MSG_TYPE_SERVER_MANAGER_CMD_REPLY = "MSG_TYPE_SERVER_MANAGER_CMD_REPLY"
MSG_TYPE_NETWORK_CONTROLLER_CMD = "MSG_TYPE_NETWORK_CONTROLLER_CMD"
MSG_TYPE_NETWORK_CONTROLLER_CMD_REPLY = "MSG_TYPE_NETWORK_CONTROLLER_CMD_REPLY"
MSG_TYPE_CLASSIFIER_CONTROLLER_CMD = "MSG_TYPE_CLASSIFIER_CONTROLLER_CMD"
MSG_TYPE_CLASSIFIER_CONTROLLER_CMD_REPLY = "MSG_TYPE_CLASSIFIER_CONTROLLER_CMD_REPLY"
MSG_TYPE_SIMULATOR_CMD = "MSG_TYPE_SIMULATOR_CMD"
MSG_TYPE_SIMULATOR_CMD_REPLY = "MSG_TYPE_SIMULATOR_CMD_REPLY"
# server manager use case
MSG_TYPE_SERVER_REPLY = "MSG_TYPE_SERVER_REPLY"
# tester use case
MSG_TYPE_TESTER_CMD = "MSG_TYPE_TESTER_CMD"

MESSAGE_AGENT_MAX_QUEUE_SIZE = 99999


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
                'messageAgent.log', level='info')
            self.logger = logConfigur.getLogger()
        self.logger.info("Init MessaageAgent.")
        self.readRabbitMQConf()
        self.msgQueues = {}
        self._threadSet = {}
        self._publisherConnection = None
        # self._consumerConnection = None # self._connectRabbitMQServer()

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
                channel.queue_declare(queue=dstQueueName, durable=True)
                channel.basic_publish(exchange='', routing_key=dstQueueName,
                    body=self._encodeMessage(message),
                    properties=pika.BasicProperties(delivery_mode = 2)
                    # make message persistent
                    )
                # self.logger.debug(" [x] Sent %r" % message)
                self.logger.debug(" [x] Sent ")
                channel.close()
            except Exception as ex:
                ExceptionProcessor(self.logger).logException(ex,
                    "MessageAgent sendMsg failed")
            finally:
                if self._publisherConnection.is_open:
                    self._publisherConnection.close()
                break

    def startRecvMsg(self,srcQueueName):
        self.logger.debug("MessageAgent.startRecvMsg() on queue {0}".format(srcQueueName))
        if srcQueueName in self.msgQueues:
            self.logger.warning("Already listening on recv queue.")
        else:
            threadLock.acquire()
            self.msgQueues[srcQueueName] = Queue.Queue()
            try:
                # start a new thread to recieve
                thread = QueueReciever(len(self._threadSet), 
                    self.rabbitMqServerIP, self.rabbitMqServerUser, self.rabbitMqServerPasswd,
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

    def getMsgCnt(self, srcQueueName):
        if srcQueueName in self.msgQueues:
            return self.msgQueues[srcQueueName].qsize()
        else:
            self.logger.error("No such msg queue. QueueName:{0}".format(srcQueueName))
            return -1

    def getMsg(self, srcQueueName, throughput=1000):
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
        # if self._consumerConnection.is_open:
        #     self._consumerConnection.close()


class QueueReciever(threading.Thread):
    def __init__(self, threadID, 
                    rabbitMqServerIP, rabbitMqServerUser, rabbitMqServerPasswd,
                    srcQueueName, msgQueue, logger):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.rabbitMqServerIP = rabbitMqServerIP
        self.rabbitMqServerUser = rabbitMqServerUser
        self.rabbitMqServerPasswd = rabbitMqServerPasswd
        self.connection = self._connectRabbitMQServer()
        self.channel = None
        self.srcQueueName = srcQueueName
        self.msgQueue = msgQueue
        self.logger = logger

    def _openConnection(self):
        if not self.connection or self.connection.is_closed:
            self.connection = self._connectRabbitMQServer()

    def _connectRabbitMQServer(self):
        credentials = pika.PlainCredentials(self.rabbitMqServerUser,
            self.rabbitMqServerPasswd)
        parameters = pika.ConnectionParameters(self.rabbitMqServerIP,
            5672, '/', credentials)
        connection = pika.BlockingConnection(parameters)
        return connection

    def run(self):
        self.logger.debug("thread QueueReciever.run().")
        self._recvMsg()

    def _recvMsg(self):
        self._openConnection()
        self._openChannel()
        while True:
            try:
                self.channel.start_consuming()
            except KeyboardInterrupt:
                self._closeChannel()
                self._closeConnection()
                return None
            # except ChannelClosed:
            #     self.logger.warning(
            #         "channel closed by broker, reconnect to broker.")
            # except ReentrancyError:
            #     self.logger.error(
            #         "The requested operation would result in unsupported"
            #         " recursion or reentrancy."
            #         "Used by BlockingConnection/BlockingChannel.")
            #     return None
            except Exception as ex:
                ExceptionProcessor(self.logger).logException(ex,
                    "MessageAgent recvMsg failed")
                self._openConnection()
                self._openChannel()

    def _openChannel(self):
        try:
            if not self.channel or self.channel.is_closed:
                self.channel = self.connection.channel()
            self.channel.queue_declare(queue=self.srcQueueName, durable=True)
            self.channel.basic_consume(queue=self.srcQueueName,
                                on_message_callback=self.callback)
            self.logger.info(' [*] _openChannel(): Waiting for messages. To exit press CTRL+C')
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                "Open channel failed!")

    def _closeChannel(self):
        if self.channel.is_open:
            self.logger.info("messageAgent get keyboardInterrupt.")
            requeued_messages = self.channel.cancel()
            self.logger.info('Channel stop consuming')
            self.channel.stop_consuming()
        elif self.channel.is_closed:
            self.logger.info("Channel has already been closed!")
        else:
            self.logger.info("Channel is closing!")

    def _closeConnection(self):
        if self.connection.is_open:
            self.connection.close()

    def callback(self, ch, method, properties, body):
        # self.logger.debug(" [x] Received %r" % body)
        self.logger.debug(" [x] Received ")
        threadLock.acquire()
        if self.msgQueue.qsize() < MESSAGE_AGENT_MAX_QUEUE_SIZE:
            self.msgQueue.put(body)
        else:
            raise ValueError("MessageAgent recv qeueu full! Drop new msg!")
        threadLock.release()
        self.logger.debug(" [x] Done")
        ch.basic_ack(delivery_tag = method.delivery_tag)