#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid
import time
import math
import copy
import base64
import cPickle
import numpy as np

import psutil

from sam.base.messageAgent import MessageAgent, SAMMessage, DISPATCHER_QUEUE, MEDIATOR_QUEUE, \
    MSG_TYPE_DISPATCHER_CMD, MSG_TYPE_REQUEST, SIMULATOR_ZONE
from sam.base.command import Command, CMD_TYPE_ADD_SFCI, CMD_TYPE_PUT_ORCHESTRATION_STATE, \
    CMD_TYPE_TURN_ORCHESTRATION_ON, CMD_TYPE_KILL_ORCHESTRATION
from sam.base.pickleIO import PickleIO
from sam.base.request import REQUEST_TYPE_ADD_SFC, REQUEST_TYPE_ADD_SFCI, \
    REQUEST_TYPE_DEL_SFCI, REQUEST_TYPE_DEL_SFC, REQUEST_TYPE_DEL_SFC
from sam.base.shellProcessor import ShellProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.orchestration import orchestrator
from sam.dispatcher.argParser import ArgParser
from sam.dispatcher.orchestratorManager import OrchestratorManager
from sam.dispatcher.config import AUTO_SCALE, ZONE_INFO_LIST
from sam.measurement.dcnInfoBaseMaintainer import DCNInfoBaseMaintainer
from sam.base.exceptionProcessor import ExceptionProcessor


class Dispatcher(object):
    def __init__(self, parallelMode=True):
        self.parallelMode = parallelMode
        self.autoScale = AUTO_SCALE
        self.oMDict = {}

        self.pIO = PickleIO()

        logConfigur = LoggerConfigurator(__name__, './log',
            'dispatcher_{0}.log'.format(self.parallelMode),
            level='debug')
        self.logger = logConfigur.getLogger()

        self.dispatcherQueueName = DISPATCHER_QUEUE
        self._messageAgent = MessageAgent(self.logger)
        self._messageAgent.startRecvMsg(self.dispatcherQueueName)

    def startDispatcher(self):
        # raise ValueError("Haven't implement")
        self._init()
        self.startRoutine()

    def _init(self):
        for zoneInfo in ZONE_INFO_LIST:
            topologyDict = self.loadTopoFromPickleFile(zoneInfo)
            self.initOrchestratorManager(zoneInfo, topologyDict)

    def loadTopoFromPickleFile(self, zoneInfo):
        topoFilePath = zoneInfo["info"]["topoFilePath"]
        self.logger.info("Loading topo file")
        topologyDict = self.pIO.readPickleFile(topoFilePath)
        self.logger.info("Loading topo file successfully.")
        return topologyDict

    def initOrchestratorManager(self, zoneInfo, topologyDict):
        podNum = zoneInfo["info"]["podNum"]
        topoType = zoneInfo["info"]["topoType"]
        zoneName = zoneInfo["zone"]
        oM = OrchestratorManager(self.parallelMode,
                                    zoneName, podNum, topoType)
        oM._updateDib(topologyDict, zoneName)
        self.logger.debug("Update dib finish!")

        # decide the orchestrator number and corresponding idx;
        oInfoList = oM.computeOrchInfoList()

        # start orchestrator instance
        for idx, oInfoDict in enumerate(oInfoList):
            # we need turn off orchestrator at initial to put state into it
            oPid = oM.initNewOrchestratorInstance(idx, oInfoDict)
            oM.addOrchInstance(oInfoDict["name"], oPid, oInfoDict)
            oM.putState2Orchestrator(oInfoDict["name"])
            oM.turnOnOrchestrator(oInfoDict["name"])
        self.oMDict[zoneName] = oM

    def startRoutine(self):
        try:
            while True:
                msgCnt = self._messageAgent.getMsgCnt(self.dispatcherQueueName)
                msg = self._messageAgent.getMsg(self.dispatcherQueueName)
                msgType = msg.getMessageType()
                if msgType == None:
                    pass
                else:
                    body = msg.getbody()
                    if self._messageAgent.isRequest(body):
                        self._requestHandler(body)
                    elif self._messageAgent.isCommandReply(body):
                        self._commandReplyHandler(body)
                    elif self._messageAgent.isCommand(body):
                        self._commandHandler(body)
                    else:
                        self.logger.error("Unknown massage body:{0}".format(body))

                # TODO: future works: keep dcn info consistency
                # sync state from orchestrator instance periodically (i.e. 5 minutes): getState(), update subZoneState into self._dib
                # store self._dib into mysql
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, 
                "Dispatcher msg handler")
        finally:
            pass

    def _requestHandler(self, request):
        # TODO: dispatch requests to different orchestrator instances
        try:
            if request.requestType == REQUEST_TYPE_ADD_SFC:
                sfc = request.attributes["sfc"]
                zoneName = request.attributes["zone"]
                # assign different SFC to different orchestrator in round robin mode, and
                # record which SFC has been mapped in which orchestrator instances.
                orchName = self.oMDict[zoneName]._selectOrchInRoundRobin()
                self.logger.warning("assign SFC to orchName:{0}".format(orchName))
                self.oMDict[zoneName]._assignSFC2Orchestrator(sfc, orchName)
                self._sendRequest2Orchestrator(request, orchName)   # we dispatch add request previously
            elif request.requestType == REQUEST_TYPE_ADD_SFCI:
                sfc = request.attributes["sfc"]
                sfci = request.attributes["sfci"]
                zoneName = request.attributes["zone"]
                orchName = self.oMDict[zoneName]._getOrchestratorNameBySFC(sfc)
                self.logger.warning("assign SFC to orchName:{0}".format(orchName))
                self.oMDict[zoneName]._assignSFCI2Orchestrator(sfci, orchName)
                self._sendRequest2Orchestrator(request, orchName)
            elif request.requestType in [REQUEST_TYPE_DEL_SFCI, REQUEST_TYPE_DEL_SFC]:
                sfc = request.attributes["sfc"]
                zoneName = request.attributes["zone"]
                orchName = self.oMDict[zoneName]._getOrchestratorNameBySFC(sfc)
                self._sendRequest2Orchestrator(request, orchName)
            else:
                self.logger.warning(
                    "Unknown request:{0}".format(request.requestType)
                    )
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                "dispatcher _requestHandler")
        finally:
            pass

    def _sendRequest2Orchestrator(self, request, orchName):
        queueName = "ORCHESTRATOR_QUEUE_{0}".format(orchName)
        msg = SAMMessage(MSG_TYPE_REQUEST, request)
        self._messageAgent.sendMsg(queueName, msg)

    def _commandReplyHandler(self, cmd):
        raise ValueError("Unimplementation _commandReplyHandler")

    def _commandHandler(self, cmd):
        raise ValueError("Unimplementation _commandHandler")


if __name__ == "__main__":
    argParser = ArgParser()
    parallelMode = argParser.getArgs()['parallelMode']

    dP = Dispatcher(parallelMode)
    dP.startDispatcher()
