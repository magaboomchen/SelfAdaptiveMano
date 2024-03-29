#!/usr/bin/python
# -*- coding: UTF-8 -*-

import ctypes
import inspect
from typing import Dict, Union

from sam.base.link import Link
from sam.base.path import DIRECTION0_PATHID_OFFSET, DIRECTION1_PATHID_OFFSET
from sam.base.sfc import SFCI
from sam.base.shellProcessor import ShellProcessor
from sam.base.messageAgent import  PUFFER_ZONE, SIMULATOR_ZONE, TURBONET_ZONE, \
                                SAMMessage, MessageAgent, \
                                MSG_TYPE_REPLY
from sam.base.messageAgentAuxillary.msgAgentRPCConf import MEASURER_IP, \
                                                            MEASURER_PORT
from sam.base.command import CommandReply
from sam.base.request import REQUEST_TYPE_GET_SFCI_STATE, Reply, \
                                REQUEST_STATE_SUCCESSFUL, \
                                REQUEST_TYPE_GET_DCN_INFO, Request
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.measurement import measurerCommandSender
from sam.dashboard.backup.dashboardInfoBaseMaintainer import DashboardInfoBaseMaintainer
from sam.measurement.dcnInfoBaseMaintainer import DCNInfoBaseMaintainer


class Measurer(object):
    def __init__(self):
        logConfigur = LoggerConfigurator(__name__, './log',
            'measurer.log', level='debug')
        self.logger = logConfigur.getLogger()

        self._dib = DCNInfoBaseMaintainer()
        # self._dib.enableDataBase("localhost", "dbAgent",
        #     "123")
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
                    elif self._messageAgent.isReply(body):
                        self._replyHandler(body)
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
            self.logger.error("Unknown request:{0}".format(
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
                # inactiveSwitches = self._dib.getInactiveSwitchesByZone(zoneName)
                # self.logger.info("inactiveSwitches is {0}".format(inactiveSwitches))
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
                self.logSFCIsDict(value)
                self._dib.updateSFCIsByZone(value, zoneName)
            else:
                self.logger.error("Unknown attributes:{0}".format(key))

    def logSFCIsDict(self, sfcisDict):
        # type: (Dict[int, SFCI]) -> None
        for sfciID, sfci in sfcisDict.items():
            self.logger.debug("sfciID is {0}".format(sfciID))
            vnfiSeq = sfci.vnfiSequence
            for vnfis in vnfiSeq:
                for vnfi in vnfis:
                    self.logger.debug("vnfis status {0}".format(vnfi.vnfiStatus))

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
                self.logger.error("Unknown attributes:{0}".format(key))
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
                self.logger.error("Unknown attributes:{0}".format(key))

    def _replyHandler(self, reply):
        # type: (CommandReply) -> None
        # self.logger.debug(reply)
        zoneName = reply.attributes['zone']
        self.logger.info("Get a command reply from {0}".format(zoneName))
        if zoneName == TURBONET_ZONE:
            self._replyHandler4TurbonetZone(reply)
        else:
            raise ValueError("Unimplement zone {0}".format(zoneName))

    def _replyHandler4TurbonetZone(self, cmdRply,):
        # type: (CommandReply) -> None
        for key,value in cmdRply.attributes.items():
            if key == 'switches':
                raise ValueError("We don't need measure it.")
            elif key == 'links':
                self.computeAllSFCILatency(value, TURBONET_ZONE)
            elif key == 'vnfis':
                raise ValueError("We don't need measure it.")
            elif key == 'zone':
                pass
            elif key == 'source':
                pass
            elif key == 'servers':
                raise ValueError("We don't need measure it.")
            elif key == 'sfcisDict':
                raise ValueError("We don't need measure it.")
            else:
                self.logger.error("Unknown attributes:{0}".format(key))

    def computeAllSFCILatency(self, links, zoneName):
        sfciDict = self._dib.getSFCIsByZone(zoneName)
        for sfciID, sfci in sfciDict.items():
            sumLatency = 0
            for pathOffsetID in [DIRECTION0_PATHID_OFFSET, DIRECTION1_PATHID_OFFSET]:
                if pathOffsetID in sfci.forwardingPathSet.primaryForwardingPath.keys():
                    fp = sfci.forwardingPathSet.primaryForwardingPath[pathOffsetID]
                    latency = self.computeForwardingPathLatency(fp, links, zoneName)
                    sumLatency += latency
            avgLatency = float(sumLatency) / 2.0
            self.logger.info("the avgLatency {0}".format(avgLatency))
            self._dib.setSFCILatency(zoneName, sfciID, avgLatency)

    def computeForwardingPathLatency(self, fp, links, zoneName):
        avgLatency = 0
        for stageIdx, segPath in enumerate(fp):
            segPathLen = len(segPath)
            for idx in range(segPathLen-1):
                srcNodeID = segPath[idx][1]
                dstNodeID = segPath[idx+1][1]
                linkLatency = self.getLinkQueueLatency(links, srcNodeID, 
                                                    dstNodeID, zoneName)
                self.logger.info("link {0}-{1}'s latency {2}".format(srcNodeID, dstNodeID, linkLatency))
                avgLatency += linkLatency
        return avgLatency

    def getLinkQueueLatency(self, links, srcID, dstID, zoneName):
        latency = 0
        if zoneName in links.keys():
            if (srcID, dstID) in links[zoneName].keys():
                link = links[zoneName][(srcID, dstID)]['link']    # type: Link
                latency = link.queueLatency
        return latency

if __name__=="__main__":
    m = Measurer()
    m.startMeasurer()
