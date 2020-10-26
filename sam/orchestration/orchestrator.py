#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.messageAgent import *
from sam.measurement.dcnInfoBaseMaintainer import *
from sam.orchestration.oDcnInfoRetriever import *
from sam.orchestration.oSFCAdder import *
from sam.orchestration.oSFCDeleter import *

LANIPPrefix = 27


class Orchestrator(object):
    def __init__(self):
        logConfigur = LoggerConfigurator(__name__, './log',
            'orchestrator.log', level='info')
        self.logger = logConfigur.getLogger()

        self._dib = DCNInfoBaseMaintainer()

        self._odir = ODCNInfoRetriever(self._dib, self.logger)

        self._osa = OSFCAdder(self._dib, self.logger)
        self._osd = OSFCDeleter(self._dib, self.logger)

        self._cm = CommandMaintainer()

        self._messageAgent = MessageAgent(self.logger)
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
                    self.logger.error("Unknown massage body:{0}".format(body))

    def _requestHandler(self, request):
        try:
            if request.requestType == REQUEST_TYPE_ADD_SFC:
                # TODO
                pass
            elif request.requestType == REQUEST_TYPE_ADD_SFCI:
                self._addRequest2DB(request)
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
                self.logger.warning(
                    "Unknown request:{0}".format(request.requestType)
                    )
        # except Exception as ex:
        #     template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        #     message = template.format(type(ex).__name__, ex.args)
        #     self.logger.error(
        #         "Orchestrator request handler error: {0}".format(message)
        #         )
        finally:
            pass

    def sendCmd(self, cmd):
        msg = SAMMessage(MSG_TYPE_MEDIATOR_CMD, cmd)
        self._messageAgent.sendMsg(MEDIATOR_QUEUE, msg)

    def _commandReplyHandler(self, cmdRply):
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
        self._cm.delCmdwithChildCmd(cmdID)

        # find the request by sfcUUID in cmd
        cmd = self._cm.getCmd(cmdID)
        request = self._getRequestFromDB(cmd.attributes['sfcUUID'])

        # update request state
        self._updateRequest2DB(request, state)

    def _addRequest2DB(self, request):
        # TODO
        pass

    def _getRequestFromDB(self, sfcUUID):
        # TODO
        pass
        return 0

    def _updateRequest2DB(self, request, state):
        # TODO
        # update request's state by retrieve requestID
        pass


if __name__=="__main__":
    ot = Orchestrator()
    ot.startOrchestrator()

