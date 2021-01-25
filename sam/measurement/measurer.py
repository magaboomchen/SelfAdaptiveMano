#!/usr/bin/python
# -*- coding: UTF-8 -*-

import base64
import time
import uuid
import subprocess
import struct
import copy

import pickle

from sam.base.server import Server
from sam.base.messageAgent import *
from sam.base.switch import *
from sam.base.sfc import *
from sam.base.command import *
from sam.base.request import *
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.dashboard.dashboardInfoBaseMaintainer import DashboardInfoBaseMaintainer
from sam.measurement.dcnInfoBaseMaintainer import *

# TODO: database agent, multiple zones


class Measurer(object):
    def __init__(self):
        logConfigur = LoggerConfigurator(__name__, './log',
            'measurer.log', level='debug')
        self.logger = logConfigur.getLogger()

        self._dib = DCNInfoBaseMaintainer()
        self._dashib = DashboardInfoBaseMaintainer("localhost", "dbAgent",
            "123")

        self._messageAgent = MessageAgent(self.logger)
        self.queueName = self._messageAgent.genQueueName(MEASURER_QUEUE)
        self._messageAgent.startRecvMsg(self.queueName)

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
        for thread in self._threadSet.itervalues():
            self.logger.debug("check thread is alive?")
            if thread.isAlive():
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
            msg = self._messageAgent.getMsg(self.queueName)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            else:
                body = msg.getbody()
                try:
                    if self._messageAgent.isRequest(body):
                        self._requestHandler(body)
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
            queueName = DCN_INFO_RECIEVER_QUEUE
            self.sendReply(rply, queueName)
        else:
            self.logger.warning("Unknown request:{0}".format(request.requestType))

    def getTopoAttributes(self):
        servers = self._dib.getServersInAllZone()
        switches = self._dib.getSwitchesInAllZone()
        links = self._dib.getLinksInAllZone()
        vnfis = self._dib.getVnfisInAllZone()
        return {'switches':switches,'links':links,'servers':servers,
            'vnfis':vnfis}

    def sendReply(self, rply, queueName):
        msg = SAMMessage(MSG_TYPE_REPLY, rply)
        self._messageAgent.sendMsg(queueName, msg)

    def _commandReplyHandler(self, cmdRply):
        self.logger.info("Get a command reply")
        self.logger.debug(cmdRply)
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
            else:
                self.logger.warning("Unknown attributes:{0}".format(key))
        self.logger.debug("dib:{0}".format(self._dib))


class MeasurerCommandSender(threading.Thread):
    def __init__(self, threadID, messageAgent, logger, dashib):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self._messageAgent = messageAgent
        self.logger = logger
        self._dashib = dashib

    def run(self):
        self.logger.debug("thread MeasurerCommandSender.run().")
        try:
            while True:
                zoneNameList = self._dashib.getAllZone()
                for zoneName in zoneNameList:
                    self.logger.debug("zoneName: {0}".format(zoneName))
                    self.sendGetTopoCmd(zoneName)
                    self.sendGetServersCmd(zoneName)
                    # TODO: self.sendGetSFCIStateCmd(zoneName)
                time.sleep(5)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex)

    def sendGetTopoCmd(self, zoneName):
        getTopoCmd = Command(CMD_TYPE_GET_TOPOLOGY, uuid.uuid1(),
            {"zone":zoneName})
        msg = SAMMessage(MSG_TYPE_MEDIATOR_CMD, getTopoCmd)
        self._messageAgent.sendMsg(MEDIATOR_QUEUE, msg)

    def sendGetServersCmd(self, zoneName):
        getServersCmd = Command(CMD_TYPE_GET_SERVER_SET, uuid.uuid1(),
            {"zone":zoneName})
        msg = SAMMessage(MSG_TYPE_MEDIATOR_CMD, getServersCmd)
        self._messageAgent.sendMsg(MEDIATOR_QUEUE, msg)

    def sendGetSFCIStateCmd(self, zoneName):
        getSFCIStateCmd = Command(CMD_TYPE_GET_SFCI_STATE, uuid.uuid1(),
            {"zone":zoneName})
        msg = SAMMessage(MSG_TYPE_MEDIATOR_CMD, getSFCIStateCmd)
        self._messageAgent.sendMsg(MEDIATOR_QUEUE, msg)


if __name__=="__main__":
    m = Measurer()
    m.startMeasurer()

