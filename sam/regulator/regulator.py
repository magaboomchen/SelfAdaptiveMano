#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
Input: recieve failure/abnormal notification command from inteligent module
Output: send del/add SFCI request to dispatcher

Get SFCI from db, check which switch/server has been used for each SFCI.

"""

import time
import ctypes
import inspect

from sam.base.pickleIO import PickleIO
from sam.base.messageAgentAuxillary.msgAgentRPCConf import REGULATOR_IP, \
                                                            REGULATOR_PORT
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.messageAgent import DISPATCHER_QUEUE, \
                                    MSG_TYPE_REQUEST, REGULATOR_QUEUE, \
                                    MessageAgent, SAMMessage
from sam.base.request import REQUEST_STATE_FAILED, REQUEST_STATE_INITIAL, \
                                REQUEST_TYPE_ADD_SFC, REQUEST_TYPE_ADD_SFCI, \
                                REQUEST_TYPE_DEL_SFC, REQUEST_TYPE_DEL_SFCI, \
                                REQUEST_TYPE_GET_DCN_INFO
from sam.base.shellProcessor import ShellProcessor
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer
from sam.regulator import regulatorRequestSender
from sam.regulator.argParser import ArgParser
from sam.regulator.config import ENABLE_REQUEST_RETRY, MAX_RETRY_NUM, \
                                    FAILURE_REQUEST_RETRY_TIMEOUT
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
        self.enableRetryFailureRequest = ENABLE_REQUEST_RETRY
        self.prevTimestamp = time.time()
        self.cmdHandler = CommandHandler(self.logger, self._messageAgent,
                                            self._oib)
        self.replyHandler = ReplyHandler(self.logger, self._messageAgent,
                                            self._oib)
        self.requestHandler = RequestHandler(self.logger, self._messageAgent,
                                            self._oib)                           

    def startRegulator(self):
        self._collectSFCIState()
        self.startRoutine()

    def _collectSFCIState(self):
        # start a new process to send command
        self.sP = ShellProcessor()
        filePath = regulatorRequestSender.__file__
        self.sP.runPythonScript(filePath)

    def startRoutine(self):
        while True:
            try:
                self.msgHandlerRoutine()
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
                self.logger.info("Retry failed request {0}".format(requestUUID))
                requestType = requestTuple[1]
                request = requestTuple[6]
                retryCnt = requestTuple[7]
                if retryCnt > MAX_RETRY_NUM:
                    self.logger.warning(" failed request {0} exceeds" \
                                        " max retry number".format(requestUUID))
                    continue
                if requestType in [REQUEST_TYPE_ADD_SFC, 
                                    REQUEST_TYPE_ADD_SFCI,
                                    REQUEST_TYPE_DEL_SFCI,
                                    REQUEST_TYPE_DEL_SFC]:
                    self._oib.updateRequestState2DB(request, REQUEST_STATE_INITIAL)
                    self._oib.incRequestRetryCnt(requestUUID)
                    msg = SAMMessage(MSG_TYPE_REQUEST, request)
                    self._messageAgent.sendMsg(DISPATCHER_QUEUE, msg)
                    self.logger.debug(" retry failed request {0}".format(requestUUID))
                elif requestType in [REQUEST_TYPE_GET_DCN_INFO]:
                    self.logger.warning("Disable retry for get dcn info request!")
                    self._oib.delRequest(requestUUID)
                else:
                    raise ValueError("Unknown request type {0}".format(requestType))

    def msgHandlerRoutine(self):
        # Listen on message
        msg = self._messageAgent.getMsg(self.regulatorQueueName)
        msgType = msg.getMessageType()
        if msgType == None:
            pass
        else:
            body = msg.getbody()
            if self._messageAgent.isRequest(body):
                self.requestHandler.handle(body)
            else:
                self.logger.error("Unknown massage body:{0}".format(body))

        msg = self._messageAgent.getMsgByRPC(REGULATOR_IP, REGULATOR_PORT)
        msgType = msg.getMessageType()
        if msgType == None:
            pass
        else:
            body = msg.getbody()
            if self._messageAgent.isCommand(body):
                self.cmdHandler.handle(body)
            elif self._messageAgent.isReply(body):
                self.replyHandler.handle(body)
            else:
                self.logger.error("Unknown massage body:{0}".format(body))
        time.sleep(1)
        self.cmdHandler.processAllRecoveryTasks()
        self.replyHandler.processAllScalingTasks()
        self.requestHandler.processAllRequestTask()

    def __del__(self):
        self.logConfigur = LoggerConfigurator(__name__, None,
            None, level='info')
        self.logger = self.logConfigur.getLogger()
        self.logger.info("Delete Regulator.")
        self.sP.killPythonScript("regulatorRequestSender.py")

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
