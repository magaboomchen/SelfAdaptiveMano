#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
import time
import uuid
import ctypes
import inspect
import threading
from typing import Dict, Union
from logging import Logger
from threading import Thread
from packaging import version

from sam.base.shellProcessor import ShellProcessor
from sam.measurement.mConfig import MEASURE_TIME_SLOT, SIMULATOR_ZONE_ONLY, TURBONET_ZONE_ONLY
from sam.base.messageAgent import MSG_TYPE_P4CONTROLLER_CMD, MSG_TYPE_SERVER_MANAGER_CMD, MSG_TYPE_SFF_CONTROLLER_CMD, MSG_TYPE_SIMULATOR_CMD, MSG_TYPE_VNF_CONTROLLER_CMD, PUFFER_ZONE, SIMULATOR_ZONE, TURBONET_ZONE, \
                                SAMMessage, MessageAgent, \
                                MSG_TYPE_REPLY, MSG_TYPE_MEDIATOR_CMD
from sam.base.messageAgentAuxillary.msgAgentRPCConf import MEASURER_IP, \
    MEASURER_PORT, P4_CONTROLLER_IP, P4_CONTROLLER_PORT, SFF_CONTROLLER_IP, \
    SFF_CONTROLLER_PORT, SIMULATOR_IP, SIMULATOR_PORT, \
    SERVER_MANAGER_IP, SERVER_MANAGER_PORT, \
    VNF_CONTROLLER_IP, VNF_CONTROLLER_PORT
from sam.base.command import Command, CMD_TYPE_GET_TOPOLOGY, \
    CMD_TYPE_GET_SERVER_SET, CMD_TYPE_GET_SFCI_STATE, CommandReply
from sam.base.request import REQUEST_TYPE_GET_SFCI_STATE, Reply, \
                                REQUEST_STATE_SUCCESSFUL, \
                                REQUEST_TYPE_GET_DCN_INFO, Request
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.measurement import measurerCommandSender
from sam.dashboard.dashboardInfoBaseMaintainer import DashboardInfoBaseMaintainer
from sam.measurement.dcnInfoBaseMaintainer import DCNInfoBaseMaintainer


class Measurer(object):
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

    def startMeasurer(self):
        self._collectTopology()
        self._runService()

    def _collectTopology(self):
        # start a new process to send command
        self.sP = ShellProcessor()
        filePath = measurerCommandSender.__file__
        self.sP.runPythonScript(filePath)

    def __del__(self):
        self.logConfigur = LoggerConfigurator(__name__, None,
            None, level='info')
        self.logger = self.logConfigur.getLogger()
        self.logger.info("Delete Measurer.")
        self.sP.killPythonScript("measurerCommandSender.py")

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
                    elif self._messageAgent.isCommandReply(body):
                        self._commandReplyHandler(body)
                    else:
                        self.logger.error("Unknown massage body")
                except Exception as ex:
                    ExceptionProcessor(self.logger).logException(ex,
                        "measurer")

    def _requestHandler(self, request):
        # type: (Request) -> None
        self.logger.info("Recv a request")
        if request.requestType == REQUEST_TYPE_GET_DCN_INFO:
            attributes = self.getTopoAttributes()
            rply = Reply(request.requestID,
                REQUEST_STATE_SUCCESSFUL, attributes)
            return rply
        elif request.requestType == REQUEST_TYPE_GET_SFCI_STATE:
            self.logger.info("Get SFCI state request.")
            attributes = self.getSFCIAttributes()
            rply = Reply(request.requestID,
                REQUEST_STATE_SUCCESSFUL, attributes)
            return rply
        else:
            self.logger.warning("Unknown request:{0}".format(
                request.requestType))

    def getTopoAttributes(self):
        servers = self._dib.getServersInAllZone()
        switches = self._dib.getSwitchesInAllZone()
        links = self._dib.getLinksInAllZone()
        sfcis = self._dib.getSFCIsInAllZone()
        return {'switches':switches, 'links':links, 'servers':servers,
                    'sfcis':sfcis}

    def getSFCIAttributes(self):
        sfcis = self._dib.getSFCIsInAllZone()
        return {'sfcis':sfcis}

    def sendReply(self, rply, dstIP, dstPort):
        msg = SAMMessage(MSG_TYPE_REPLY, rply)
        self._messageAgent.sendMsgByRPC(dstIP, dstPort, msg)

    def _commandReplyHandler(self, cmdRply):
        # type: (CommandReply) -> None
        # self.logger.debug(cmdRply)
        zoneName = cmdRply.attributes['zone']
        self.logger.info("Get a command reply from {0}".format(zoneName))
        if zoneName == SIMULATOR_ZONE:
            self._cmdRplyHandler4SimulatorZone(cmdRply, zoneName)
        elif zoneName == TURBONET_ZONE:
            self._cmdRplyHandler4TurbonetZone(cmdRply, zoneName)
        elif zoneName == PUFFER_ZONE:
            self._cmdRplyHandler4PUFFERZone(cmdRply, zoneName)
        else:
            raise ValueError("Unimplement zone {0}".format(zoneName))

    def _cmdRplyHandler4SimulatorZone(self, cmdRply, zoneName):
        # type: (CommandReply, Union[SIMULATOR_ZONE, TURBONET_ZONE]) -> None
        for key,value in cmdRply.attributes.items():
            if key == 'switches':
                self._dib.updateSwitchesByZone(value, zoneName)
            elif key == 'links':
                self._dib.updateLinksByZone(value, zoneName)
            elif key == 'servers':
                self._dib.updateServersByZone(value, zoneName)
            elif key == 'vnfis':
                # This code path is deprecated.
                self._dib.updateVnfisByZone(value, zoneName)
            elif key == 'zone':
                pass
            elif key == 'source':
                pass
            elif key == 'sfcisDict':
                self._dib.updateSFCIsByZone(value, zoneName)
            else:
                self.logger.warning("Unknown attributes:{0}".format(key))

    def _cmdRplyHandler4TurbonetZone(self, cmdRply, zoneName):
        # type: (CommandReply, Union[SIMULATOR_ZONE, TURBONET_ZONE]) -> None
        for key,value in cmdRply.attributes.items():
            if key == 'switches':
                raise ValueError("We don't need measure it.")
            elif key == 'links':
                raise ValueError("We don't need measure it.")
            elif key == 'vnfis':
                raise ValueError("We don't need measure it.")
            elif key == 'zone':
                pass
            elif key == 'source':
                pass
            elif key == 'servers':
                self._dib.updateServersByZone(value, zoneName)
                # self._dib.updateSwitch2ServerLinksByZone(zoneName)
            elif key == 'sfcisDict':
                self._dib.updatePartialSFCIsByZone(value, zoneName)
                # # debug
                # sfcis = self._dib.getSFCIsByZone(zoneName)
                # self.logger.debug("print sfci")
                # for sfciID, sfci in sfcis.items():
                #     self.logger.debug("{0}, {1}, {2}, {3}".format(sfciID, sfci,
                #                                     sfci.sloRealTimeValue.throughput,
                #                                     sfci.sloRealTimeValue.dropRate))
            else:
                self.logger.warning("Unknown attributes:{0}".format(key))
        # self.logger.debug("dib:{0}".format(self._dib))

    def _cmdRplyHandler4PUFFERZone(self, cmdRply, zoneName):
        # type: (CommandReply, Union[SIMULATOR_ZONE, TURBONET_ZONE]) -> None
        raise ValueError("Haven't implement and test!")
        for key,value in cmdRply.attributes.items():
            if key == 'switches':
                self._dib.updateSwitchesByZone(value, zoneName)
            elif key == 'links':
                self._dib.updateLinksByZone(value, zoneName)
            elif key == 'vnfis':
                raise ValueError("We don't need measure it.")
            elif key == 'zone':
                pass
            elif key == 'source':
                pass
            elif key == 'servers':
                self._dib.updateServersByZone(value, zoneName)
                self._dib.updateSwitch2ServerLinksByZone(zoneName)
            elif key == 'sfcisDict':
                self._dib.updatePartialSFCIsByZone(value, zoneName)
            else:
                self.logger.warning("Unknown attributes:{0}".format(key))


if __name__=="__main__":
    m = Measurer()
    m.startMeasurer()
