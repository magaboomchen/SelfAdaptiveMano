#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
Usage:
    from sam.base.messageAgent import SAMMessage, MessageAgent, TURBONET_ZONE, \
                                        REGULATOR_QUEUE, MEASURER_QUEUE, \
                                        DEFINABLE_MEASURER_QUEUE, ABNORMAL_DETECTOR_QUEUE

Use case 1 - abnormal detector:
    # Thread 1
    # send Request to definable measurer to get datacenter infomation
    while True:
        time.sleep(3)
        msgType = MSG_TYPE_REQUEST
        request = Request(0, uuid.uuid1(), REQUEST_TYPE_GET_DCN_INFO)
        msg = SAMMessage(msgType, request)
        mA.sendMsgByRPC(DEFINABLE_MEASURER_IP, DEFINABLE_MEASURER_PORT, msg)

    # Thread 2
    # recv message in a While loop from a grpc socket: 
    mA.startMsgReceiverRPCServer(ABNORMAL_DETECTOR_IP, ABNORMAL_DETECTOR_PORT)
    while True:
        msg = mA.getMsgByRPC(ABNORMAL_DETECTOR_IP, ABNORMAL_DETECTOR_PORT)

    # send "abnormal handle command" to REGULATOR_QUEUE (PS: regulator can handle abnormal and failure)
    queueName = REGULATOR_QUEUE
    mA = MessageAgent()
    msgType = MSG_TYPE_ABNORMAL_DETECTOR_CMD
    attr = None # Store all abnormal and failure in this variable
    cmd = Command(CMD_TYPE_HANDLE_FAILURE_ABNORMAL, uuid.uuid1(), attributes={attr})
    msg = SAMMessage(msgType, cmd)
    mA.sendMsg(queueName, msg)

Use case 2 - definable measurer:
    # Thread 1
    # send Request to measurer to get datacenter infomation
    while True:
        time.sleep(3)
        msgType = MSG_TYPE_REQUEST
        request = Request(0, uuid.uuid1(), REQUEST_TYPE_GET_DCN_INFO)
        msg = SAMMessage(msgType, request)
        mA.sendMsgByRPC(MEASURER_IP, MEASURER_PORT, msg)

    # Thread 2
    # recv message in a While loop from a grpc socket: 
    mA.startMsgReceiverRPCServer(DEFINABLE_MEASURER_IP, DEFINABLE_MEASURER_PORT)
    while True:
        msg = mA.getMsgByRPC(DEFINABLE_MEASURER_IP, DEFINABLE_MEASURER_PORT)
        msgType = msg.getMessageType() # Maybe request from abnormal detector, or dcn info from measurer

    # send message to abnormal detector
    msg = SAMMessage(msgType, cmd)
    mA.sendMsgByRPC(SIMULATOR_IP, SIMULATOR_PORT, msg)

Use case 3 - elastic orchestrator(regulator):
    # recv message in a While loop from REGULATOR_QUEUE
    queueName = REGULATOR_QUEUE
    mA.startRecvMsg(queueName)
    while True:
        msg = mA.getMsg(queueName)

"""

from packaging import version
import sys
if sys.version >= '3':
    import queue as Queue
    import _pickle as cPickle
else:
    import Queue
    import cPickle
import time
import uuid
import json
import socket
import ctypes
import inspect
import threading
from concurrent import futures

import pika
import grpc

from sam.base.pickleIO import PickleIO
from sam.base.request import Request, Reply
from sam.base.command import Command, CommandReply
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.messageAgentAuxillary.msgAgentRPCConf import MAX_MESSAGE_LENGTH, \
    P4_CONTROLLER_PORT, TEST_PORT
import sam.base.messageAgentAuxillary.messageAgent_pb2 as messageAgent_pb2
import sam.base.messageAgentAuxillary.messageAgent_pb2_grpc as messageAgent_pb2_grpc

threadLock = threading.Lock()

# zone name
MININET_ZONE = "MININET_ZONE"
TURBONET_ZONE = "TURBONET_ZONE"
SIMULATOR_ZONE = "SIMULATOR_ZONE"
PUFFER_ZONE = "PUFFER_ZONE"
PROJECT3_ZONE = "PROJECT3_ZONE"
PICA8_ZONE = "PICA8_ZONE"
DEFAULT_ZONE = "DEFAULT_ZONE"

# formal queue type
REQUEST_PROCESSOR_QUEUE = "REQUEST_PROCESSOR_QUEUE"
DCN_INFO_RECIEVER_QUEUE = "DCN_INFO_RECIEVER_QUEUE"
MEASURER_QUEUE = "MEASURER_QUEUE"
DEFINABLE_MEASURER_QUEUE = "DEFINABLE_MEASURER_QUEUE"
ABNORMAL_DETECTOR_QUEUE = "ABNORMAL_DETECTOR_QUEUE"
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
REGULATOR_QUEUE = "REGULATOR_QUEUE"
P4CONTROLLER_QUEUE = "P4CONTROLLER_QUEUE"
TEST_QUEUE = "TEST_QUEUE"

# general use case
MSG_TYPE_STRING = "MSG_TYPE_STRING"
MSG_TYPE_REQUEST = "MSG_TYPE_REQUEST"
MSG_TYPE_REPLY = "MSG_TYPE_REPLY"
# command send to abnormal detector
MSG_TYPE_ABNORMAL_DETECTOR_CMD = "MSG_TYPE_ABNORMAL_DETECTOR_CMD"
# command send to dispather
MSG_TYPE_DISPATCHER_CMD = "MSG_TYPE_DISPATCHER_CMD"
# command send to orchestrator / command reply from mediator orchestrator
MSG_TYPE_ORCHESTRATOR_CMD = "MSG_TYPE_ORCHESTRATOR_CMD"
# command send to mediator / command reply from mediator
MSG_TYPE_MEDIATOR_CMD = "MSG_TYPE_MEDIATOR_CMD"
MSG_TYPE_MEDIATOR_CMD_REPLY = "MSG_TYPE_MEDIATOR_CMD_REPLY"
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
MSG_TYPE_P4CONTROLLER_CMD = "MSG_TYPE_P4CONTROLLER_CMD"
MSG_TYPE_P4CONTROLLER_CMD_REPLY = "MSG_TYPE_P4CONTROLLER_CMD_REPLY"
MSG_TYPE_TURBONET_CONTROLLER_CMD = "MSG_TYPE_TURBONET_CONTROLLER_CMD"
MSG_TYPE_TURBONET_CONTROLLER_CMD_REPLY = "MSG_TYPE_TURBONET_CONTROLLER_CMD_REPLY"
# server manager use case
MSG_TYPE_SERVER_REPLY = "MSG_TYPE_SERVER_REPLY"
# tester use case
MSG_TYPE_TESTER_CMD = "MSG_TYPE_TESTER_CMD"
# regulator
MSG_TYPE_REGULATOR_CMD = "MSG_TYPE_REGULATOR_CMD"

MESSAGE_AGENT_MAX_QUEUE_SIZE = 99999


class SAMMessage(object):
    def __init__(self, msgType, body):
        self._msgType = msgType # can not be a type()
        self._msgID = uuid.uuid1()
        self._body = body
        self._source = None

    def getMessageType(self):
        return self._msgType

    def getMessageID(self):
        return self._msgID

    def getbody(self):
        return self._body

    def setSource(self, source):
        self._source = source

    def getSource(self):
        return self._source

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
            # Can't run file logger when call __del__() methods
            # self.logConfigur = LoggerConfigurator(__name__, './log',
            #     'messageAgent.log', level='info')
            self.logConfigur = LoggerConfigurator(__name__, None,
                None, level='info')
            self.logger = self.logConfigur.getLogger()
        self.logger.info("Init MessaageAgent.")
        self.readRabbitMQConf()
        self.msgQueues = {}
        self._threadSet = {}
        self._publisherConnection = None
        self.listenIP = None
        self.listenPort = None
        self.gRPCChannel = None
        self.gRPCServersList = []
        self.pIO = PickleIO()

    def readRabbitMQConf(self):
        filePath = __file__.split("/messageAgent.py")[0] + '/rabbitMQConf.json'
        with open(filePath, 'r') as jsonfile:
            json_string = json.load(jsonfile)
            self.rabbitMqServerIP = str(json_string["RABBITMQSERVERIP"])
            self.rabbitMqServerUser = str(json_string["RABBITMQSERVERUSER"])
            self.rabbitMqServerPasswd = str(json_string["RABBITMQSERVERPASSWD"])
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
                self.logger.debug(" [x] Sent ")
                channel.close()
            except Exception as ex:
                ExceptionProcessor(self.logger).logException(ex,
                    "MessageAgent sendMsg failed")
            finally:
                if self._publisherConnection.is_open:
                    self._publisherConnection.close()
                break

    def startRecvMsg(self, srcQueueName):
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

    def deleteQueue(self, queueName):
        while True:
            try:
                self._publisherConnection = self._connectRabbitMQServer()
                channel = self._publisherConnection.channel()
                channel.queue_purge(queue=queueName)
                self.logger.debug(" Delete queueu {0} successfully!".format(queueName))
                channel.close()
            except Exception as ex:
                ExceptionProcessor(self.logger).logException(ex,
                    "MessageAgent delete queue failed temporally. Retry")
            finally:
                if self._publisherConnection.is_open:
                    self._publisherConnection.close()
                break

    def sendMsgByRPC(self, dstIP, dstPort, message):
        if self.listenIP == None or self.listenPort == None:
            raise ValueError("Unset listen IP and port.")
        self.logger.info("gRPC listen dstIP {0}, dstPort {1}".format(dstIP, dstPort))
        self.gRPCChannel = grpc.insecure_channel(
            '{0}:{1}'.format(dstIP, dstPort),
            options=[
                ('grpc.max_send_message_length', MAX_MESSAGE_LENGTH),
                ('grpc.max_receive_message_length', MAX_MESSAGE_LENGTH),
            ],
        )

        stub = messageAgent_pb2_grpc.MessageStorageStub(channel=self.gRPCChannel)

        cnt = 5
        while True:
            try:
                source = {"comType":"RPC",
                    "srcIP": self.listenIP,
                    "srcPort": self.listenPort
                }
                message.setSource(source)
                pickles = self._encodeMessage(message)
                pickles = bytes(pickles)
                req = messageAgent_pb2.Pickle(picklebytes=pickles)
                response = stub.Store(req)

                self.logger.info("response is {0}".format(response))
                if response.booly:
                    break
            except grpc.RpcError as e:
                if cnt%5==0:
                    # ouch!
                    # lets print the gRPC error message
                    # which is "Length of `Name` cannot be more than 10 characters"
                    # self.logger.error(e.details())
                    # lets access the error code, which is `INVALID_ARGUMENT`
                    # `type` of `status_code` is `grpc.StatusCode`
                    status_code = e.code()
                    # should print `INVALID_ARGUMENT`
                    # self.logger.error(status_code.name)
                    # should print `(3, 'invalid argument')`
                    # self.logger.error(status_code.value)
                    self.logger.error("connecting socket {0}:{1} failed. " \
                        "details: {2}; " \
                        "statusCodeName: {3}; statusCodeValue: {4}".format(
                            dstIP, dstPort,
                            e.details(), status_code.name, status_code.value
                        ))
                    # want to do some specific action based on the error?
                    if grpc.StatusCode.INVALID_ARGUMENT == status_code:
                        # do your stuff here
                        pass
            except Exception as ex:
                ExceptionProcessor(self.logger).logException(ex,
                    "messageAgent")
            finally:
                time.sleep(1)
                cnt = cnt + 1

        self.gRPCChannel.close()

    def getOpenSocketPort(self):
        while True:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("", 0))
            s.listen(1)
            port = s.getsockname()[1]
            s.close()
            if P4_CONTROLLER_PORT < port or port < TEST_PORT:
                return port

    def startMsgReceiverRPCServer(self, listenIP, listenPort):
        self.listenIP = listenIP
        self.listenPort = listenPort
        srcQueueName = "{0}:{1}".format(listenIP, listenPort)
        if srcQueueName in self.msgQueues:
            self.logger.warning("Already listening on recv socket.")
        else:
            self.msgQueues[srcQueueName] = Queue.Queue()
            server = grpc.server(
                futures.ThreadPoolExecutor(max_workers=12),
                options=[
                    ('grpc.max_send_message_length', MAX_MESSAGE_LENGTH),
                    ('grpc.max_receive_message_length', MAX_MESSAGE_LENGTH),
                ],
            )
            messageAgent_pb2_grpc.add_MessageStorageServicer_to_server(MsgStorageServicer(self.msgQueues[srcQueueName]), server)

            self.logger.info('Starting server. Listening on port {0}.'.format(listenPort))
            server.add_insecure_port('{0}:{1}'.format(listenIP, listenPort))
            server.start()
            self.gRPCServersList.append(server)

    def getMsgByRPC(self, listenIP, listenPort):
        msg = self.getMsg("{0}:{1}".format(listenIP, listenPort))
        return msg

    def _encodeMessage(self, message):
        return self.pIO.obj2Pickle(message)

    def _decodeMessage(self, message):
        return self.pIO.pickle2Obj(message)

    def __del__(self):
        # Can't run file logger when call __del__() methods
        self.logger.info("Delete MessageAgent.")
        for srcQueueName, thread in self._threadSet.items():
            self.logger.debug("check thread is alive?")
            if version.parse(sys.version.split(' ')[0]) \
                                    >= version.parse('3.9'):
                threadLiveness = thread.is_alive()
            else:
                threadLiveness = thread.isAlive()
            if threadLiveness:
                self.logger.info("Kill thread: %d" %thread.ident)
                self._async_raise(thread.ident, KeyboardInterrupt)
                thread.join()

        self.logger.info("Disconnect from RabbiMQServer.")
        self._disConnectRabbiMQServer()

        self.logger.info("close gRPC channel")
        if self.gRPCChannel != None:
            self.gRPCChannel.close()

        if sys.version > '3':
            self.logger.warning("Bugs: Unimplement gRPC server " \
                "stop function because of the unlimited wait time.")
            # for server in self.gRPCServersList:
            #     server.stop(None)
        else:
            self.logger.info("stop gRPC servers")
            for server in self.gRPCServersList:
                server.wait_for_termination()

    def _async_raise(self, tid, exctype):
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


class MsgStorageServicer(messageAgent_pb2_grpc.MessageStorageServicer):
    def __init__(self, msgQueue):
        self.msgQueue = msgQueue

    def Store(self, request, context):
        pickles = request.picklebytes
        data = pickles
        if self.msgQueue.qsize() < MESSAGE_AGENT_MAX_QUEUE_SIZE:
            self.msgQueue.put(data)
        else:
            raise ValueError("MessageAgent recv qeueu full! Drop new msg!")
        return messageAgent_pb2.Status(booly=True)


class QueueReciever(threading.Thread):
    def __init__(self, threadID, 
                    rabbitMqServerIP, rabbitMqServerUser, rabbitMqServerPasswd,
                    srcQueueName, msgQueue, logger):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.rabbitMqServerIP = rabbitMqServerIP
        self.rabbitMqServerUser = rabbitMqServerUser
        self.rabbitMqServerPasswd = rabbitMqServerPasswd
        self.connection = None
        self.channel = None
        self.srcQueueName = srcQueueName
        self.msgQueue = msgQueue
        self.logger = logger

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
                self.logger.info("msgAgent recv thread get keyboardInterrupt, quit recv().")
                return None
            except Exception as ex:
                ExceptionProcessor(self.logger).logException(ex,
                                    "MessageAgent recvMsg failed")
                self._logChannelStatus()
                self._logConnectionStatus()
                self._closeConnection()
                self._openConnection()
                self._openChannel()

    def _openConnection(self):
        self.logger.info("Opening connection!")
        if not self.connection or self.connection.is_closed:
            self.connection = self._connectRabbitMQServer()

    def _connectRabbitMQServer(self):
        credentials = pika.PlainCredentials(self.rabbitMqServerUser,
            self.rabbitMqServerPasswd)
        parameters = pika.ConnectionParameters(self.rabbitMqServerIP,
            5672, '/', credentials)
        connection = pika.BlockingConnection(parameters)
        return connection

    def _closeConnection(self):
        self.logger.info("Closing connection!")
        if self.connection.is_open:
            self.connection.close()
            self.connection = None

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
            self.logger.info('Channel is running! Close it.')
            requeued_messages = self.channel.cancel()
            self.channel.stop_consuming()
        elif self.channel.is_closed:
            self.logger.info("Channel has already been closed!")
        else:
            self.logger.info("Channel is closing!")

    def _logChannelStatus(self):
        if self.channel.is_open:
            self.logger.info('Channel is running! Close it.')
        elif self.channel.is_closed:
            self.logger.info("Channel has already been closed!")
        else:
            self.logger.info("Channel is closing!")

    def _logConnectionStatus(self):
        if self.connection.is_open:
            self.logger.info("Connection is opened!")
        elif self.connection.is_closed:
            self.logger.info("Connection is closed!")
        else:
            self.logger.info("Unknown connection status.")

    def callback(self, ch, method, properties, body):
        self.logger.debug(" [x] Received ")
        threadLock.acquire()
        if self.msgQueue.qsize() < MESSAGE_AGENT_MAX_QUEUE_SIZE:
            self.msgQueue.put(body)
        else:
            raise ValueError("MessageAgent recv qeueu full! Drop new msg!")
        threadLock.release()
        self.logger.debug(" [x] Done")
        ch.basic_ack(delivery_tag = method.delivery_tag)
