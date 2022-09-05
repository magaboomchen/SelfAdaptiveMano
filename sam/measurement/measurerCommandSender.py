#!/usr/bin/python
# -*- coding: UTF-8 -*-

import time
import uuid
from sam.base.request import REQUEST_TYPE_GET_LINK_INFO, Request

from sam.measurement.mConfig import MEASURE_TIME_SLOT, SIMULATOR_ZONE_ONLY, TURBONET_ZONE_ONLY
from sam.base.messageAgent import MSG_TYPE_P4CONTROLLER_CMD, MSG_TYPE_REQUEST, MSG_TYPE_SERVER_MANAGER_CMD, \
    MSG_TYPE_SFF_CONTROLLER_CMD, MSG_TYPE_SIMULATOR_CMD, MSG_TYPE_VNF_CONTROLLER_CMD, \
    SIMULATOR_ZONE, TURBONET_ZONE, SAMMessage, MessageAgent
from sam.base.messageAgentAuxillary.msgAgentRPCConf import DEFINABLE_MEASURER_IP, DEFINABLE_MEASURER_PORT, MEASURER_IP, \
    MEASURER_PORT, P4_CONTROLLER_IP, P4_CONTROLLER_PORT, SFF_CONTROLLER_IP, \
    SFF_CONTROLLER_PORT, SIMULATOR_IP, SIMULATOR_PORT, \
    SERVER_MANAGER_IP, SERVER_MANAGER_PORT, \
    VNF_CONTROLLER_IP, VNF_CONTROLLER_PORT
from sam.base.command import Command, CMD_TYPE_GET_TOPOLOGY, \
    CMD_TYPE_GET_SERVER_SET, CMD_TYPE_GET_SFCI_STATE
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.dashboard.backup.dashboardInfoBaseMaintainer import DashboardInfoBaseMaintainer


class MeasurerCommandSender(object):
    def __init__(self):
        logConfigur = LoggerConfigurator(__name__, './log',
            'measurerCommandSender.log', level='debug')
        self.logger = logConfigur.getLogger()

        self._messageAgent = MessageAgent(self.logger)
        self._messageAgent.setListenSocket(MEASURER_IP, MEASURER_PORT)

        self._dashib = DashboardInfoBaseMaintainer("localhost", "dbAgent",
            "123", reInitialTable=False)

    def run(self):
        self.logger.debug("MeasurerCommandSender.run().")
        while True:
            try:
                zoneNameList = self._dashib.getAllZone()
                if SIMULATOR_ZONE_ONLY:
                    zoneNameList = [SIMULATOR_ZONE]
                if TURBONET_ZONE_ONLY:
                    zoneNameList = [TURBONET_ZONE]
                self.logger.debug("zoneNameList is {0}".format(zoneNameList))
                for zoneName in zoneNameList:
                    self.logger.debug("zoneName: {0}".format(zoneName))
                    self.sendGetTopoCmd(zoneName)
                    self.sendGetServersCmd(zoneName)
                    self.sendGetSFCIStatusCmd(zoneName)
                    if zoneName == TURBONET_ZONE:
                        self.sendGetTurbonetLinksRequest()
            except Exception as ex:
                ExceptionProcessor(self.logger).logException(ex)
            finally:
                time.sleep(MEASURE_TIME_SLOT)

    def sendGetTopoCmd(self, zoneName):
        getTopoCmd = Command(CMD_TYPE_GET_TOPOLOGY, uuid.uuid1(),
            {"zone":zoneName})
        if zoneName == SIMULATOR_ZONE:
            msg = SAMMessage(MSG_TYPE_SIMULATOR_CMD, getTopoCmd)
            self._messageAgent.sendMsgByRPC(SIMULATOR_IP, SIMULATOR_PORT, msg)
        elif zoneName == TURBONET_ZONE:
            pass
        else:
            raise ValueError("Unimplement zone {0}".format(zoneName))

    def sendGetTurbonetLinksRequest(self):
        listenIP = self._messageAgent.getListenIP()
        listenPort = self._messageAgent.getListenPort()
        reqSource = {"srcIP": listenIP, "srcPort": listenPort}
        getLinkReq = Request(0, uuid.uuid1(), REQUEST_TYPE_GET_LINK_INFO,
                                requestSource=reqSource)
        msg = SAMMessage(MSG_TYPE_REQUEST, getLinkReq)
        self._messageAgent.sendMsgByRPC(DEFINABLE_MEASURER_IP, 
                                        DEFINABLE_MEASURER_PORT,
                                        msg)

    def sendGetServersCmd(self, zoneName):
        getServersCmd = Command(CMD_TYPE_GET_SERVER_SET, uuid.uuid1(),
            {"zone":zoneName})
        if zoneName == SIMULATOR_ZONE:
            msg = SAMMessage(MSG_TYPE_SIMULATOR_CMD, getServersCmd)
            self._messageAgent.sendMsgByRPC(SIMULATOR_IP, SIMULATOR_PORT, \
                                            msg)
        elif zoneName == TURBONET_ZONE:
            msg = SAMMessage(MSG_TYPE_SERVER_MANAGER_CMD, getServersCmd)
            self._messageAgent.sendMsgByRPC(SERVER_MANAGER_IP, \
                                            SERVER_MANAGER_PORT, msg)
        else:
            raise ValueError("Unimplement zone {0}".format(zoneName))

    def sendGetSFCIStatusCmd(self, zoneName):
        getSFCIStateCmd = Command(CMD_TYPE_GET_SFCI_STATE, uuid.uuid1(),
            {"zone":zoneName})
        if zoneName == SIMULATOR_ZONE:
            msg = SAMMessage(MSG_TYPE_SIMULATOR_CMD, getSFCIStateCmd)
            self._messageAgent.sendMsgByRPC(SIMULATOR_IP, SIMULATOR_PORT, msg)
        elif zoneName == TURBONET_ZONE:
            msg = SAMMessage(MSG_TYPE_SFF_CONTROLLER_CMD, getSFCIStateCmd)
            self._messageAgent.sendMsgByRPC(SFF_CONTROLLER_IP, \
                                            SFF_CONTROLLER_PORT, msg)
            msg = SAMMessage(MSG_TYPE_P4CONTROLLER_CMD, getSFCIStateCmd)
            self._messageAgent.sendMsgByRPC(P4_CONTROLLER_IP, \
                                            P4_CONTROLLER_PORT, msg)
            msg = SAMMessage(MSG_TYPE_VNF_CONTROLLER_CMD, getSFCIStateCmd)
            self._messageAgent.sendMsgByRPC(VNF_CONTROLLER_IP, \
                                            VNF_CONTROLLER_PORT, msg)
        else:
            raise ValueError("Unimplement zone {0}".format(zoneName))


if __name__ == "__main__":
    mCS = MeasurerCommandSender()
    mCS.run()
