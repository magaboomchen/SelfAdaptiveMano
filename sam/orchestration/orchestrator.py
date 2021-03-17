#!/usr/bin/python
# -*- coding: UTF-8 -*-

import time
import sys
if sys.version > '3':
    import queue as Queue
else:
    import Queue

from sam.base.messageAgent import *
from sam.base.request import Request, Reply
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.measurement.dcnInfoBaseMaintainer import *
from sam.orchestration.oDcnInfoRetriever import *
from sam.orchestration.oSFCAdder import *
from sam.orchestration.oSFCDeleter import *
from sam.orchestration.oConfig import *
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer


class Orchestrator(object):
    def __init__(self):
        # time.sleep(15)   # wait for other basic module boot

        logConfigur = LoggerConfigurator(__name__, './log',
            'orchestrator.log', level='debug')
        self.logger = logConfigur.getLogger()

        self._dib = DCNInfoBaseMaintainer()
        self._oib = OrchInfoBaseMaintainer("localhost", "dbAgent", "123")
        self._cm = CommandMaintainer()

        self._odir = ODCNInfoRetriever(self._dib, self.logger)
        self._osa = OSFCAdder(self._dib, self.logger)
        self._osd = OSFCDeleter(self._dib, self._oib, self.logger)

        self._messageAgent = MessageAgent(self.logger)
        self._messageAgent.startRecvMsg(ORCHESTRATOR_QUEUE)

        self._requestBatchQueue = Queue.Queue()
        self._batchMode = True
        self._batchSize = BATCH_SIZE

    def startOrchestrator(self):
        while True:
            msg = self._messageAgent.getMsg(ORCHESTRATOR_QUEUE)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            else:
                body = msg.getbody()
                if self._messageAgent.isRequest(body):
                    self._requestHandler(body)
                elif self._messageAgent.isCommandReply(body):
                    self._commandReplyHandler(body)
                else:
                    self.logger.error("Unknown massage body:{0}".format(body))

    def _requestHandler(self, request):
        try:
            if request.requestType == REQUEST_TYPE_ADD_SFC:
                self._odir.getDCNInfo()
                cmd = self._osa.genAddSFCCmd(request)
                self._cm.addCmd(cmd)
                self._oib.addSFCRequestHandler(request, cmd)
                self.sendCmd(cmd)
            elif request.requestType == REQUEST_TYPE_ADD_SFCI:
                if self._batchMode == False:
                    raise ValueError("Deprecated function: genAddSFCICmd"
                        "Please use batch mode!")
                    # self._odir.getDCNInfo()
                    # cmd = self._osa.genAddSFCICmd(request)
                    # self._cm.addCmd(cmd)
                    # self._oib.addSFCIRequestHandler(request, cmd)
                    # self.sendCmd(cmd)
                else:
                    self._requestBatchQueue.put(request)
                    if self._requestBatchQueue.qsize() >= self._batchSize:
                        self._odir.getDCNInfo()
                        requestCmdBatch = self._osa.genABatchOfRequestAndAddSFCICmds(
                            self._requestBatchQueue)
                        for (request, cmd) in requestCmdBatch:
                            self._cm.addCmd(cmd)
                            self._oib.addSFCIRequestHandler(request, cmd)
                            self.sendCmd(cmd)
            elif request.requestType == REQUEST_TYPE_DEL_SFCI:
                cmd = self._osd.genDelSFCICmd(request)
                self.logger.debug("orchestrator classifier's serverID: {0}".format(
                    cmd.attributes['sfc'].directions[0]['ingress'].getServerID()
                ))
                self._cm.addCmd(cmd)
                self._oib.delSFCIRequestHandler(request, cmd)
                self.sendCmd(cmd)
            elif request.requestType == REQUEST_TYPE_DEL_SFC:
                cmd = self._osd.genDelSFCCmd(request)
                self._cm.addCmd(cmd)
                self._oib.delSFCRequestHandler(request, cmd)
                self.sendCmd(cmd)
            else:
                self.logger.warning(
                    "Unknown request:{0}".format(request.requestType)
                    )
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                "orchestrator _requestHandler")
            self._oib.updateRequestState2DB(request, REQUEST_STATE_FAILED)
        finally:
            pass

    def sendCmd(self, cmd):
        msg = SAMMessage(MSG_TYPE_MEDIATOR_CMD, cmd)
        self._messageAgent.sendMsg(MEDIATOR_QUEUE, msg)

    def _commandReplyHandler(self, cmdRply):
        try:
            self.logger.info("Get a command reply")
            # update cmd state
            cmdID = cmdRply.cmdID
            state = cmdRply.cmdState
            if not self._cm.hasCmd(cmdID):
                self.logger.error(
                    "Unknown command reply, cmdID:{0}".format(cmdID)
                    )
                return 
            self._cm.changeCmdState(cmdID, state)
            self._cm.addCmdRply(cmdID, cmdRply)
            cmdType = self._cm.getCmdType(cmdID)
            self.logger.info("Command:{0}, cmdType:{1}, state:{2}".format(
                cmdID, cmdType, state))

            # find the request by sfcUUID in cmd
            cmd = self._cm.getCmd(cmdID)
            cmdType = self._cm.getCmdType(cmdID)
            if cmdType == CMD_TYPE_ADD_SFC or cmdType == CMD_TYPE_DEL_SFC:
                request = self._oib.getRequestByCmdID(cmd.cmdID)
            elif cmdType == CMD_TYPE_ADD_SFCI or cmdType == CMD_TYPE_DEL_SFCI:
                request = self._oib.getRequestByCmdID(cmd.cmdID)
            else:
                raise ValueError("Unkonw cmd type: {0}".format(cmdType))

            # update request state
            self._oib.cmdRplyHandler(request, state)
            self._cm.delCmdwithChildCmd(cmdID)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, 
                "Orchestrator commandReply handler")
        finally:
            pass


if __name__=="__main__":
    ot = Orchestrator()
    ot.startOrchestrator()
