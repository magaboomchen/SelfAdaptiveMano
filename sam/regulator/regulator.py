#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
Input: recieve failure/abnormal notification command from inteligent module
Output: send del/add SFCI request to dispatcher

Get SFCI from db, check which switch/server has been used for each SFCI.

"""

import sys
import time
import ctypes
import inspect
from packaging import version

from sam.base.pickleIO import PickleIO
from sam.base.messageAgentAuxillary.msgAgentRPCConf import REGULATOR_IP, REGULATOR_PORT
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.messageAgent import DISPATCHER_QUEUE, \
                                    MSG_TYPE_REQUEST, REGULATOR_QUEUE, \
                                    MessageAgent, SAMMessage
from sam.base.request import REQUEST_STATE_FAILED, REQUEST_STATE_INITIAL, \
                                REQUEST_TYPE_ADD_SFC, REQUEST_TYPE_ADD_SFCI, \
                                REQUEST_TYPE_DEL_SFC, REQUEST_TYPE_DEL_SFCI, \
                                REQUEST_TYPE_GET_DCN_INFO
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer
from sam.regulator.argParser import ArgParser
from sam.regulator.config import FAILURE_REQUEST_RETRY_TIMEOUT, MAX_RETRY_NUM
from sam.regulator.regulatorRequestSender import RegulatorRequestSender
from sam.regulator.replyHandler import ReplyHandler
from sam.regulator.commandHandler import CommandHandler
from sam.regulator.requestHandler import RequestHandler


class Regulator(object):
    def __init__(self):
        self.pIO = PickleIO()
        self._oib = OrchInfoBaseMaintainer("localhost", "dbAgent", "123",
                                            False)
        logConfigur = LoggerConfigurator(__name__, './log',
            'regulator.log',
            level='debug')
        self.logger = logConfigur.getLogger()
        self.regulatorQueueName = REGULATOR_QUEUE
        self._messageAgent = MessageAgent(self.logger)
        self._messageAgent.startRecvMsg(self.regulatorQueueName)
        self._messageAgent.startMsgReceiverRPCServer(REGULATOR_IP,
                                                    REGULATOR_PORT)
        self.enableRetryFailureRequest = False
        self.prevTimestamp = time.time()
        self.cmdHandler = CommandHandler(self.logger, self._messageAgent,
                                            self._oib)
        self.replyHandler = ReplyHandler(self.logger, self._messageAgent,
                                            self._oib)
        self.requestHandler = RequestHandler(self.logger, self._messageAgent,
                                            self._oib)                           
        self._threadSet = {}

    def startRegulator(self):
        self._collectSFCIState()
        self.startRoutine()

    def _collectSFCIState(self):
        # start a new thread to send command
        threadID = len(self._threadSet)
        thread = RegulatorRequestSender(threadID, self._messageAgent,
                                                        self.logger)
        self._threadSet[threadID] = thread
        thread.setDaemon(True)
        thread.start()

    def startRoutine(self):
        try:
            while True:
                self.requestReplyHandlerRoutine()
                self.commandHandlerRoutine()
                self.retryFailureRequestRoutine()
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, 
                "Regulator msg handler")
        finally:
            pass

    def retryFailureRequestRoutine(self):
        currTimestamp = time.time()
        deltTimestamp = currTimestamp - self.prevTimestamp
        if deltTimestamp > FAILURE_REQUEST_RETRY_TIMEOUT:
            self.prevTimestamp = time.time()
            if self.enableRetryFailureRequest:
                self.retryFailureRequests()

    def retryFailureRequests(self):
        requestTupleList = self._oib.getAllRequest(condition=" STATE = '{0}' ".format(REQUEST_STATE_FAILED))
        # " REQUEST_UUID, REQUEST_TYPE, SFC_UUID, SFCIID, CMD_UUID, STATE, PICKLE, RETRY_CNT "
        for requestTuple in requestTupleList:
            state = requestTuple[5]
            if state == REQUEST_STATE_FAILED:
                requestUUID = requestTuple[0]
                requestType = requestTuple[1]
                request = requestTuple[6]
                retryCnt = requestTuple[7]
                if retryCnt > MAX_RETRY_NUM:
                    self.logger.warning(" failed request {0} exceeds" \
                                        " max retry number".format(request))
                    continue
                if requestType in [REQUEST_TYPE_ADD_SFC, 
                                    REQUEST_TYPE_ADD_SFCI,
                                    REQUEST_TYPE_DEL_SFCI,
                                    REQUEST_TYPE_DEL_SFC]:
                    self._oib.updateRequestState(requestUUID, REQUEST_STATE_INITIAL)
                    self._oib.incRequestRetryCnt(requestUUID)
                    msg = SAMMessage(MSG_TYPE_REQUEST, request)
                    self._messageAgent.sendMsg(DISPATCHER_QUEUE, msg)
                    self.logger.debug(" retry failed request {0}".format(request))
                elif requestType in [REQUEST_TYPE_GET_DCN_INFO]:
                    self.logger.warning("Disable retry for get dcn info request!")
                    self._oib.delRequest(requestUUID)
                else:
                    raise ValueError("Unknown request type {0}".format(requestType))

    def commandHandlerRoutine(self):
        # Listen on command
        msg = self._messageAgent.getMsg(self.regulatorQueueName)
        msgType = msg.getMessageType()
        if msgType == None:
            pass
        else:
            body = msg.getbody()
            if self._messageAgent.isCommand(body):
                self.cmdHandler.handle(body)
            else:
                self.logger.error("Unknown massage body:{0}".format(body))
        self.cmdHandler.processAllRecoveryTasks()

    def requestReplyHandlerRoutine(self):
        # Listen on request/reply
        msg = self._messageAgent.getMsgByRPC(REGULATOR_IP, REGULATOR_PORT)
        msgType = msg.getMessageType()
        if msgType == None:
            pass
        else:
            body = msg.getbody()
            if self._messageAgent.isReply(body):
                self.replyHandler.handle(body)
            elif self._messageAgent.isRequest(body):
                self.requestHandler.handle(body)
            else:
                self.logger.error("Unknown massage body:{0}".format(body))
        self.replyHandler.processAllScalingTasks()
        self.requestHandler.processAllRequestTask()

    def __del__(self):
        self.logger.info("Delete Regulator.")
        self.logger.debug(self._threadSet)
        for key, thread in self._threadSet.items():
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


if __name__ == "__main__":
    argParser = ArgParser()
    dP = Regulator()
    dP.startRegulator()
