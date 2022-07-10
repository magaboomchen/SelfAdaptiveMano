#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
import time
import uuid
import ctypes
import inspect
import threading
from packaging import version

from sam.base.messageAgent import SIMULATOR_ZONE, SAMMessage, MessageAgent, \
    MEASURER_QUEUE, MSG_TYPE_REPLY, MSG_TYPE_MEDIATOR_CMD, MEDIATOR_QUEUE
from sam.base.messageAgentAuxillary.msgAgentRPCConf import MEASURER_IP, \
    MEASURER_PORT, P4_CONTROLLER_IP, P4_CONTROLLER_PORT, SFF_CONTROLLER_IP, \
    SFF_CONTROLLER_PORT, SIMULATOR_IP, SIMULATOR_PORT, NETWORK_CONTROLLER_IP, \
    NETWORK_CONTROLLER_PORT, SERVER_MANAGER_IP, SERVER_MANAGER_PORT, \
    VNF_CONTROLLER_IP, VNF_CONTROLLER_PORT
from sam.base.command import Command, CMD_TYPE_GET_TOPOLOGY, \
    CMD_TYPE_GET_SERVER_SET, CMD_TYPE_GET_SFCI_STATE, CMD_TYPE_GET_VNFI_STATE
from sam.base.request import Reply, REQUEST_STATE_SUCCESSFUL, \
                                REQUEST_TYPE_GET_DCN_INFO
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor
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
            "123")

        self._messageAgent = MessageAgent(self.logger)
        self.queueName = self._messageAgent.genQueueName(MEASURER_QUEUE)
        # self._messageAgent.startRecvMsg(self.queueName)
        self._messageAgent.startMsgReceiverRPCServer(MEASURER_IP, MEASURER_PORT)

        self._threadSet = {}
        self.logger.info("self.queueName:{0}".format(self.queueName))

    def startMeasurer(self):
        self._collectTopology()
        self._runService()

    def _collectTopology(self):
        # start a new thread to send command
        threadID = len(self._threadSet)
        thread = MeasurerCommandSender(threadID, self._messageAgent,
            self.logger, self._dashib)
        self._threadSet[threadID] = thread
        thread.setDaemon(True)
        thread.start()

    def __del__(self):
        self.logger.info("Delete Measurer.")
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

    def _runService(self):
        while True:
            # msg = self._messageAgent.getMsg(self.queueName)
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
        self.logger.info("Recv a request")
        if request.requestType == REQUEST_TYPE_GET_DCN_INFO:
            attributes = self.getTopoAttributes()
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
        vnfis = self._dib.getVnfisInAllZone()
        return {'switches':switches, 'links':links, 'servers':servers,
            'vnfis':vnfis}

    def sendReply(self, rply, dstIP, dstPort):
        msg = SAMMessage(MSG_TYPE_REPLY, rply)
        # self._messageAgent.sendMsg(queueName, msg)
        self._messageAgent.sendMsgByRPC(dstIP, dstPort, msg)

    def _commandReplyHandler(self, cmdRply):
        self.logger.info("Get a command reply")
        # self.logger.debug(cmdRply)
        zoneName = cmdRply.attributes['zone']
        for key,value in cmdRply.attributes.items():
            if key == 'switches':
                self._dib.updateSwitchesByZone(value, zoneName)
            elif key == 'links':
                self._dib.updateLinksByZone(value, zoneName)
            elif key == 'servers':
                self._dib.updateServersByZone(value, zoneName)
                self._dib.updateSwitch2ServerLinksByZone(zoneName)
            elif key == 'vnfis':
                self._dib.updateVnfisByZone(value, zoneName)
            elif key == 'zone':
                pass
            elif key == 'source':
                pass
            else:
                self.logger.warning("Unknown attributes:{0}".format(key))
        # self.logger.debug("dib:{0}".format(self._dib))


class MeasurerCommandSender(threading.Thread):
    def __init__(self, threadID, messageAgent, logger, dashib):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self._messageAgent = messageAgent
        self.logger = logger
        self._dashib = dashib

    def run(self):
        self.logger.debug("thread MeasurerCommandSender.run().")
        while True:
            try:
                zoneNameList = self._dashib.getAllZone()
                # zoneNameList = [SIMULATOR_ZONE]
                self.logger.debug("zoneNameList is {0}".format(zoneNameList))
                for zoneName in zoneNameList:
                    self.logger.debug("zoneName: {0}".format(zoneName))
                    self.sendGetTopoCmd(zoneName)
                    self.sendGetServersCmd(zoneName)
                    self.sendGetSFCIStatusCmd(zoneName)
                    self.sendGetVNFIStateCmd(zoneName)
            except Exception as ex:
                ExceptionProcessor(self.logger).logException(ex)
            finally:
                time.sleep(5)

    def sendGetTopoCmd(self, zoneName):
        getTopoCmd = Command(CMD_TYPE_GET_TOPOLOGY, uuid.uuid1(),
            {"zone":zoneName})
        msg = SAMMessage(MSG_TYPE_MEDIATOR_CMD, getTopoCmd)
        if zoneName == SIMULATOR_ZONE:
            self._messageAgent.sendMsgByRPC(SIMULATOR_IP, SIMULATOR_PORT, msg)
        else:
            pass

    def sendGetServersCmd(self, zoneName):
        getServersCmd = Command(CMD_TYPE_GET_SERVER_SET, uuid.uuid1(),
            {"zone":zoneName})
        msg = SAMMessage(MSG_TYPE_MEDIATOR_CMD, getServersCmd)
        if zoneName == SIMULATOR_ZONE:
            self._messageAgent.sendMsgByRPC(SIMULATOR_IP, SIMULATOR_PORT, \
                                            msg)
        else:
            self._messageAgent.sendMsgByRPC(SERVER_MANAGER_IP, \
                                            SERVER_MANAGER_PORT, msg)

    def sendGetSFCIStatusCmd(self, zoneName):
        getSFCIStateCmd = Command(CMD_TYPE_GET_SFCI_STATE, uuid.uuid1(),
            {"zone":zoneName})
        msg = SAMMessage(MSG_TYPE_MEDIATOR_CMD, getSFCIStateCmd)
        if zoneName == SIMULATOR_ZONE:
            self._messageAgent.sendMsgByRPC(SIMULATOR_IP, SIMULATOR_PORT, msg)
        else:
            self._messageAgent.sendMsgByRPC(SFF_CONTROLLER_IP, \
                                            SFF_CONTROLLER_PORT, msg)
            self._messageAgent.sendMsgByRPC(P4_CONTROLLER_IP, \
                                            P4_CONTROLLER_PORT, msg)

    def sendGetVNFIStateCmd(self, zoneName):
        getVNFIStateCmd = Command(CMD_TYPE_GET_VNFI_STATE, uuid.uuid1(),
            {"zone":zoneName})
        msg = SAMMessage(MSG_TYPE_MEDIATOR_CMD, getVNFIStateCmd)
        if zoneName == SIMULATOR_ZONE:
            self._messageAgent.sendMsgByRPC(SIMULATOR_IP, SIMULATOR_PORT, msg)
        else:
            self._messageAgent.sendMsgByRPC(VNF_CONTROLLER_IP, \
                                            VNF_CONTROLLER_PORT, msg)
            self._messageAgent.sendMsgByRPC(P4_CONTROLLER_IP, \
                                            P4_CONTROLLER_PORT, msg)


if __name__=="__main__":
    m = Measurer()
    m.startMeasurer()
