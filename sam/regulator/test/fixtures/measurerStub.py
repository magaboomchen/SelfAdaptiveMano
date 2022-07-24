#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.command import CMD_TYPE_ADD_SFCI
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.messageAgent import SAMMessage, MessageAgent, MSG_TYPE_REPLY
from sam.base.messageAgentAuxillary.msgAgentRPCConf import MEASURER_IP, MEASURER_PORT
from sam.base.request import REQUEST_TYPE_GET_SFCI_STATE, Reply, REQUEST_STATE_SUCCESSFUL
from sam.base.vnf import VNFIStatus
from sam.measurement.dcnInfoBaseMaintainer import DCNInfoBaseMaintainer
from sam.dashboard.dashboardInfoBaseMaintainer import DashboardInfoBaseMaintainer


class MeasurerStub(object):
    def __init__(self):
        logConfigur = LoggerConfigurator(__name__, './log',
            'measurer.log', level='debug')
        self.logger = logConfigur.getLogger()

        self._dib = DCNInfoBaseMaintainer()
        self._dib.enableDataBase("localhost", "dbAgent",
            "123")
        self._dashib = DashboardInfoBaseMaintainer("localhost", "dbAgent",
            "123", reInitialTable=False)

        self._messageAgent = MessageAgent(self.logger)
        self._messageAgent.startMsgReceiverRPCServer(MEASURER_IP, MEASURER_PORT)

        self.getSFCIStateCmdCnt = 0
        self.oldInputTrafficAmount = 0

        self._threadSet = {}

    def addSFCIData(self, sfci, zoneName):
        self._dib.updateSFCIsByZone(sfci, zoneName)

    def startMeasurer(self):
        self._runService()

    def _runService(self):
        while True:
            msg = self._messageAgent.getMsgByRPC(MEASURER_IP, MEASURER_PORT)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            else:
                body = msg.getbody()
                source = msg.getSource()
                try:
                    if self._messageAgent.isRequest(body):
                        rply = self._requestHandler(body)
                        self.sendReply(rply, source["srcIP"], source["srcPort"])
                    elif self._messageAgent.isCommand(body):
                        rply = self._cmdHandler(body)
                    else:
                        self.logger.error("Unknown massage body")
                except Exception as ex:
                    ExceptionProcessor(self.logger).logException(ex,
                        "measurer")

    def _requestHandler(self, request):
        self.logger.info("Recv a request")
        if request.requestType == REQUEST_TYPE_GET_SFCI_STATE:
            attributes = self.getSFCIAttributes()
            rply = Reply(request.requestID,
                REQUEST_STATE_SUCCESSFUL, attributes)
            return rply
        else:
            self.logger.warning("Unknown request:{0}".format(
                request.requestType))

    def getSFCIAttributes(self):
        self.getSFCIStateCmdCnt += 1
        sfcisInAllZoneDict = self._dib.getSFCIsInAllZone()
        for zone, sfciDict in sfcisInAllZoneDict.items():
            for sfciID, sfci in sfciDict.items():
                for vnfis in sfci.vnfiSequence:
                    for vnfi in vnfis:
                        scalingRatio = self.getSclaingRatio()
                        self.currentInputTrafficAmount = self.oldInputTrafficAmount \
                                                            + 1 * 1e06 * scalingRatio
                        inputTrafficAmount = self.currentInputTrafficAmount
                        self.logger.info("scalingRatio is {0}".format(scalingRatio))
                        inputPacketAmount = int(inputTrafficAmount / 64.0)
                        vnfi.vnfiStatus = VNFIStatus(
                            inputTrafficAmount = inputTrafficAmount,
                            inputPacketAmount = inputPacketAmount,
                            outputTrafficAmount = inputTrafficAmount,
                            outputPacketAmount = inputPacketAmount
                            )
        # self.logger.info("sfcisInAllZoneDict is {0}".format(sfcisInAllZoneDict))
        self.oldInputTrafficAmount = self.currentInputTrafficAmount
        return {'sfcis':sfcisInAllZoneDict}

    def getSclaingRatio(self):
        stageNum = int(self.getSFCIStateCmdCnt / 10)
        if stageNum % 2 == 0:
            return 1.0
        else:
            return 8.0

    def sendReply(self, rply, dstIP, dstPort):
        msg = SAMMessage(MSG_TYPE_REPLY, rply)
        self._messageAgent.sendMsgByRPC(dstIP, dstPort, msg)

    def _cmdHandler(self, cmd):
        if cmd.cmdType == CMD_TYPE_ADD_SFCI:
            sfci = cmd.attributes["sfci"]
            zoneName = cmd.attributes["zone"]
            self._dib.addSFCIByZone(sfci, zoneName)
        else:
            raise ValueError("Unknown command type {0}".format(cmd.cmdType))


if __name__ == "__main__":
    mS = MeasurerStub()
    mS.startMeasurer()