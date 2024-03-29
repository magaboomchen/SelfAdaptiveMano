#!/usr/bin/python
# -*- coding: UTF-8 -*-

from typing import Dict, Union

from sam.base.command import CMD_TYPE_FAILURE_ABNORMAL_RESUME, \
                                CMD_TYPE_HANDLE_FAILURE_ABNORMAL, Command, CommandReply
from sam.base.commandMaintainer import CommandMaintainer
from sam.base.messageAgent import SIMULATOR_ZONE, TURBONET_ZONE, MessageAgent, \
                                    SAMMessage, \
                                    DISPATCHER_QUEUE, MSG_TYPE_REQUEST
from sam.base.pickleIO import PickleIO
from sam.base.request import REQUEST_TYPE_ADD_SFC, REQUEST_TYPE_ADD_SFCI, \
    REQUEST_TYPE_DEL_SFCI, REQUEST_TYPE_DEL_SFC, REQUEST_TYPE_DEL_SFC, Request
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.sfc import SFC
from sam.dispatcher.argParser import ArgParser
from sam.dispatcher.orchestratorManager.orchestratorManager import OrchestratorManager
from sam.dispatcher.config import AUTO_SCALE, RE_INIT_TABLE, ZONE_INFO_LIST
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer


class Dispatcher(object):
    def __init__(self, parallelMode=True):
        self.parallelMode = parallelMode
        self.autoScale = AUTO_SCALE
        self.oMDict = {}    # type: Dict[Union[SIMULATOR_ZONE, TURBONET_ZONE], OrchestratorManager]

        self.pIO = PickleIO()

        logConfigur = LoggerConfigurator(__name__, './log',
            'dispatcher_{0}.log'.format(self.parallelMode),
            level='debug')
        self.logger = logConfigur.getLogger()

        self.dispatcherQueueName = DISPATCHER_QUEUE
        self._messageAgent = MessageAgent(self.logger)
        self._messageAgent.startRecvMsg(self.dispatcherQueueName)

        self._cm = CommandMaintainer()

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

        # reInit orchestartor database
        self._oib = OrchInfoBaseMaintainer("localhost", "dbAgent",
                                            "123", RE_INIT_TABLE)

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
        # type: (Request) -> None
        self.logger.info("Get a request {0}".format(request.requestType))
        try:
            if request.requestType == REQUEST_TYPE_ADD_SFC:
                sfc = request.attributes["sfc"] # type: SFC
                zoneName = request.attributes["zone"]
                # assign different SFC to different orchestrator in round robin mode, and
                # record which SFC has been mapped in which orchestrator instances.
                oM = self.oMDict[zoneName]
                orchName = oM.getOrchestratorNameBySFC(sfc)
                if orchName == None:
                    orchName = oM.selectOrchInRoundRobin()
                    if orchName == None:
                        raise ValueError("Unavailable orchestrator.")
                    else:
                        oM.assignSFC2Orchestrator(sfc, orchName)
                else:
                    if not oM.isOrchestratorValidRuntimeState(orchName):
                        self.logger.info("Need to migrate SFC to other orchestrator")
                        if oM.isAllSFCIsOfASFCAreDeletedOrInitFailed(orchName, sfc.sfcUUID):
                            oM.removeSFCFromOrchestrator(orchName, sfc.sfcUUID)
                            orchName = oM.selectOrchInRoundRobin()
                            self.logger.info("migrate SFC to new orchestrator {0}".format(orchName))
                            if orchName == None:
                                raise ValueError("Unavailable orchestrator.")
                            else:
                                oM.assignSFC2Orchestrator(sfc, orchName)
                self.logger.warning("assign SFC to orchName:{0}".format(orchName))
                self._sendRequest2Orchestrator(request, orchName)   # we dispatch add request previously
            elif request.requestType == REQUEST_TYPE_ADD_SFCI:
                sfc = request.attributes["sfc"]
                sfci = request.attributes["sfci"]
                zoneName = request.attributes["zone"]
                oM = self.oMDict[zoneName]
                orchName = oM.getOrchestratorNameBySFC(sfc)
                self.logger.warning("assign SFC to orchName:{0}".format(orchName))
                oM.assignSFCI2Orchestrator(sfc.sfcUUID, sfci, orchName)
                self._sendRequest2Orchestrator(request, orchName)
            elif request.requestType in [REQUEST_TYPE_DEL_SFCI, REQUEST_TYPE_DEL_SFC]:
                sfc = request.attributes["sfc"]
                zoneName = request.attributes["zone"]
                oM = self.oMDict[zoneName]
                orchName = oM.getOrchestratorNameBySFC(sfc)
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
        # type: (Request, str) -> None
        queueName = "ORCHESTRATOR_QUEUE_{0}".format(orchName)
        msg = SAMMessage(MSG_TYPE_REQUEST, request)
        self._messageAgent.sendMsg(queueName, msg)

    def _commandReplyHandler(self, cmdRply):
        # type: (CommandReply) -> None
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
            self.logger.info("CommandID:{0}, cmdType:{1}, state:{2}".format(
                cmdID, cmdType, state))

            zoneName = cmdRply.attributes['zoneName']
            runtimeState = cmdRply.attributes['runtimeState']
            orchestrationName = cmdRply.attributes['orchestrationName']
            oM = self.oMDict[zoneName]
            oM.setOrchestratorRuntimeState(orchestrationName, runtimeState)

            self._cm.delCmdwithChildCmd(cmdID)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, 
                "Dispatcher commandReply handler")
        finally:
            pass

    def _commandHandler(self, cmd):
        # type: (Command) -> None
        try:
            self.logger.info("Get a command.")
            if cmd.cmdType in [CMD_TYPE_HANDLE_FAILURE_ABNORMAL,
                                CMD_TYPE_FAILURE_ABNORMAL_RESUME]:
                self.logger.info("Get {0}".format(cmd.cmdType))
                allZoneDetectionDict = cmd.attributes["allZoneDetectionDict"]   # type: Dict
                for zoneName, detectionDict in allZoneDetectionDict.items():
                    oM = self.oMDict[zoneName]
                    orchestratorDict = oM.getOrchestratorDict()
                    for orchName, orchInfoDict in orchestratorDict.items():
                        childCmd = oM.genUpdateEquipmentStateCmd(detectionDict)
                        self._cm.addCmd(childCmd)
                        queueName = "ORCHESTRATOR_QUEUE_{0}".format(orchName)
                        oM.sendCmd(childCmd, queueName)
            else:
                pass
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, 
                "Regualtor command handler")
        finally:
            pass


if __name__ == "__main__":
    argParser = ArgParser()
    parallelMode = argParser.getArgs()['parallelMode']

    dP = Dispatcher(parallelMode)
    dP.startDispatcher()
