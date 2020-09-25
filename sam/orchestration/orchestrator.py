#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging

from sam.base.messageAgent import *
from sam.measurement.dcnInfoBaseMaintainer import *
from sam.orchestration.oDcnInfoRetriever import *
from sam.orchestration.oSFCAdder import *
from sam.orchestration.oSFCDeleter import *

LANIPPrefix = 27


class Orchestrator(object):
    def __init__(self):
        self._dib = DCNInfoBaseMaintainer()
        self._odir = ODCNInfoRetriever(self._dib, self._messageAgent)
        self._osa = OSFCAdder(self._dib)
        self._osd = OSFCDeleter(self._dib)

        self._cm = CommandMaintainer()

        self._messageAgent = MessageAgent()
        self._messageAgent.startRecvMsg(ORCHESTRATOR_QUEUE)

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
                    logging.error("Unknown massage body:{0}".format(body))

    def _requestHandler(self, request):
        try:
            if request.requestType == REQUEST_TYPE_ADD_SFCI:
                # self._addRequest2DB()
                self._odir.getDCNInfo()
                cmd = self._osa.genAddSFCICmd(request)
                self._cm.addCmd(cmd)
                self.sendCmd(cmd)
            elif request.requestType == REQUEST_TYPE_DEL_SFCI:
                cmd = self._osd.genDelSFCICmd(request)
                self._cm.addCmd(cmd)
                self.sendCmd(cmd)
            elif request.requestType == REQUEST_TYPE_DEL_SFC:
                cmd = self._osd.genDelSFCCmd(request)
                self._cm.addCmd(cmd)
                self.sendCmd(cmd)
            else:
                logging.warning(
                    "Unknown request:{0}".format(request.requestType)
                    )
        # except Exception as ex:
        #     template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        #     message = template.format(type(ex).__name__, ex.args)
        #     logging.error(
        #         "Orchestrator request handler error: {0}".format(message)
        #         )
        finally:
            pass

    def sendCmd(self, cmd):
        msg = SAMMessage(MSG_TYPE_MEDIATOR_CMD, cmd)
        self._messageAgent.sendMsg(MEDIATOR_QUEUE, msg)

    def _commandReplyHandler(self, cmdRply):
        logging.info("Get a command reply")
        # update cmd state
        cmdID = cmdRply.cmdID
        state = cmdRply.cmdState
        if not self._cm.hasCmd(cmdID):
            logging.error(
                "Unknown command reply, cmdID:{0}".format(cmdID)
                )
            return 
        self._cm.changeCmdState(cmdID, state)
        self._cm.addCmdRply(cmdID, cmdRply)
        cmdType = self._cm.getCmdType(cmdID)
        logging.info("Command:{0}, cmdType:{1}, state:{2}".format(
            cmdID, cmdType, state))
        self._cm.delCmdwithChildCmd(cmdID)

    def _addRequest2DB(self):
        # TODO
        pass

if __name__=="__main__":
    logging.basicConfig(level=logging.INFO)

    ot = Orchestrator()
    ot.startOrchestrator()

