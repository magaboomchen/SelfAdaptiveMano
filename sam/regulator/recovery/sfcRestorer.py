#!/usr/bin/python
# -*- coding: UTF-8 -*-

from typing import Dict, List
from sam.base.pickleIO import PickleIO

from sam.base.request import REQUEST_TYPE_ADD_SFC, REQUEST_TYPE_ADD_SFCI
from sam.base.requestGenerator import RequestGenerator
from sam.base.sfc import SFC, SFCI
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.dispatcher.config import ZONE_INFO_LIST
from sam.measurement.dcnInfoBaseMaintainer import DCNInfoBaseMaintainer
from sam.regulator.config import MAX_RETRY_NUM
from sam.regulator.recovery.detectionDataMaintainer import DetectionDataMaintainer
from sam.regulator.recovery.noticeAnalyzer import NoticeAnalyzer
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer
from sam.regulator.recovery.recoveryTaskMaintainer import RecoveryTaskMaintainer
from sam.base.command import CMD_TYPE_FAILURE_ABNORMAL_RESUME, \
                                CMD_TYPE_HANDLE_FAILURE_ABNORMAL, Command
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.messageAgent import DISPATCHER_QUEUE, MSG_TYPE_DISPATCHER_CMD, \
                                    MSG_TYPE_REQUEST, MessageAgent, SAMMessage
from sam.base.sfcConstant import STATE_ACTIVE, STATE_DELETED, STATE_IN_PROCESSING, \
                                    STATE_INACTIVE, STATE_INIT_FAILED, \
                                    STATE_RECOVER_MODE, STATE_SCALING_OUT_MODE, \
                                    STATE_UNDELETED
from sam.regulator.recovery.recoveryTask import RECOVERY_TASK_STATE_ADDING_SFCI, \
                                                RECOVERY_TASK_STATE_DELETING_SFC, \
                                                RECOVERY_TASK_STATE_DELETING_SFCI, RECOVERY_TASK_STATE_FAILED, RECOVERY_TASK_STATE_FINISH, \
                                                RECOVERY_TASK_STATE_READY, \
                                                RECOVERY_TASK_STATE_WAITING, \
                                                RECOVERY_TASK_STATE_WAITING_TO_DELETE_SFC, \
                                                RECOVERY_TASK_TYPE_SFC, \
                                                RECOVERY_TASK_TYPE_SFCI


class SFCRestorer(object):
    def __init__(self, msgAgent,    # type: MessageAgent
                oib                 # type: OrchInfoBaseMaintainer
                ):
        logConfigur = LoggerConfigurator(__name__, './log',
            'SFCRestorer.log',
            level='debug')
        self.logger = logConfigur.getLogger()
        self._messageAgent = msgAgent
        self._oib = oib
        self._dib = DCNInfoBaseMaintainer()
        self.rTM = RecoveryTaskMaintainer()
        self.nA = NoticeAnalyzer(oib, self.rTM)
        self.rG = RequestGenerator()
        self.dM = DetectionDataMaintainer()

        self.pIO = PickleIO()
        self.loadDib()

    def loadDib(self):
        for zoneInfo in ZONE_INFO_LIST:
            topologyDict = self.loadTopoFromPickleFile(zoneInfo)
            zoneName = zoneInfo["zone"]
            self.updateDib(topologyDict, zoneName)

    def loadTopoFromPickleFile(self, zoneInfo):
        topoFilePath = zoneInfo["info"]["topoFilePath"]
        self.logger.info("Loading topo file")
        topologyDict = self.pIO.readPickleFile(topoFilePath)
        self.logger.info("Loading topo file successfully.")
        return topologyDict

    def updateDib(self, topologyDict, zoneName):
        self._dib.updateServersByZone(topologyDict["servers"],
                                        zoneName)
        self._dib.updateSwitchesByZone(topologyDict["switches"],
                                        zoneName)
        self._dib.updateLinksByZone(topologyDict["links"],
                                        zoneName)
        self.logger.info("update dib successfully!")

    def handle(self, cmd):
        # type: (Command) -> None
        try:
            self.logger.info("Get a command reply")
            if cmd.cmdType == CMD_TYPE_HANDLE_FAILURE_ABNORMAL:
                self.failureAbnormalHandler(cmd)
            elif cmd.cmdType == CMD_TYPE_FAILURE_ABNORMAL_RESUME:
                self.resumeHandler(cmd)
            else:
                pass
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, 
                "Regualtor command handler")
        finally:
            pass

    def resumeHandler(self, cmd):
        # type: (Command) -> None
        allZoneDetectionDict = cmd.attributes["allZoneDetectionDict"]   # type: Dict[str, Dict]
        self.logger.info("allZoneDetectionDict is {0}".format(allZoneDetectionDict))
        self._sendCmd2Dispatcher(cmd)
        self.dM.processResumeData(allZoneDetectionDict)

    def failureAbnormalHandler(self, cmd):
        # type: (Command) -> None
        allZoneDetectionDict = cmd.attributes["allZoneDetectionDict"]   # type: Dict[str, Dict]
        self.logger.info("allZoneDetectionDict is {0}".format(allZoneDetectionDict))
        self._sendCmd2Dispatcher(cmd)
        allZoneDetectionDict = self.dM.deleteDuplicateData(allZoneDetectionDict)
        self.dM.addDetectionDict(allZoneDetectionDict)
        self.handleDetectionDict(allZoneDetectionDict)

    def handleDetectionDict(self, allZoneDetectionDict):
        affectedSFCITupleList = self.nA.getAffectedSFCITupleList(allZoneDetectionDict)
        for sfciID, sfc, recoveryTaskState, recoveryTaskType in affectedSFCITupleList:
            sfcUUID = sfc.sfcUUID
            if sfc.isAutoRecovery():
                if not self.rTM.hasRecoveryTask(sfcUUID, sfciID, recoveryTaskType):
                    self.rTM.addRecoveryTask(sfcUUID, sfciID, 
                                                recoveryTaskType,
                                                recoveryTaskState)
                else:
                    self.rTM.addWaitingRecoveryTask(sfcUUID, sfciID,
                                                    recoveryTaskType,
                                                    recoveryTaskState)

    def processAllDetectionNotice(self):
        allZoneDetectionDict = self.dM.getAllZoneDetectionDict()
        self.handleDetectionDict(allZoneDetectionDict)

    def processAllRecoveryTasks(self):
        self.rTM.clearTimeOutTasks()
        self.rTM.clearRedundantTasks()
        self.rTM.loadWaitingTasks()
        recoveryTasksTupleList = self.rTM.getRecoveryTasksTupleList()
        self.logger.info("recoveryTasksTupleList {0}".format(recoveryTasksTupleList))
        for sfcUUID, recoveryTaskType, sfciID, recoveryTaskState in recoveryTasksTupleList:
            sfcState = self._oib.getSFCState(sfcUUID)
            sfciState = self._oib.getSFCIState(sfciID)
            sfc = self._oib.getSFC4DB(sfcUUID)  # type: SFC
            sfci = self._oib.getSFCI4DB(sfciID) # type: SFCI
            zoneName = self._oib.getSFCZone4DB(sfcUUID)
            if recoveryTaskState == RECOVERY_TASK_STATE_WAITING:
                if self.isReadyToRecover(sfcState, sfciState):
                    self.logger.info("ready to recover.")
                    self.updateSFCIAndSFCState2RecoveryMode(sfciID, sfcUUID)
                    self.rTM.updateRecoveryTask(sfcUUID, sfciID, recoveryTaskType,
                            recoveryTaskState=RECOVERY_TASK_STATE_READY)
            elif recoveryTaskState == RECOVERY_TASK_STATE_READY:
                if self._oib.isDelSFCIValidState(sfci.sfciID):
                    req = self.rG.genDelSFCIRequest(sfc, sfci, zoneName)
                    self.rTM.addRequest2Task(sfcUUID, recoveryTaskType, sfciID, req)
                    self._sendRequest2Dispatcher(req)
                    self.rTM.updateRecoveryTask(sfcUUID, sfciID, recoveryTaskType,
                                recoveryTaskState=RECOVERY_TASK_STATE_DELETING_SFCI)
                else:
                    if sfciState in [STATE_DELETED, STATE_INIT_FAILED]:
                        self.rTM.updateRecoveryTask(sfcUUID, sfciID, recoveryTaskType,
                                    recoveryTaskState=RECOVERY_TASK_STATE_DELETING_SFCI)
                    else:
                        pass
            elif recoveryTaskState == RECOVERY_TASK_STATE_DELETING_SFCI:
                self.logger.debug("sfciState is {0}".format(sfciState))
                if sfciState in [STATE_DELETED, STATE_INIT_FAILED]:
                    if recoveryTaskType == RECOVERY_TASK_TYPE_SFCI:
                        sfciID = sfci.sfciID
                        req = self.rG.genAddSFCIRequest(sfc, SFCI(sfciID), zoneName)
                        self.rTM.addRequest2Task(sfcUUID, recoveryTaskType, sfciID, req)
                        self._sendRequest2Dispatcher(req)
                        self.rTM.updateRecoveryTask(sfcUUID, sfciID, recoveryTaskType,
                                recoveryTaskState=RECOVERY_TASK_STATE_ADDING_SFCI)
                    elif recoveryTaskType == RECOVERY_TASK_TYPE_SFC:
                        self.rTM.updateRecoveryTask(sfcUUID, sfciID, recoveryTaskType,
                                recoveryTaskState=RECOVERY_TASK_STATE_WAITING_TO_DELETE_SFC)
                        if self._oib.isAllSFCIDeletedOrInitFailed(sfcUUID):
                            req = self.rG.genDelSFCRequest(sfc, zoneName)
                            self.rTM.addRequest2Task(sfcUUID, recoveryTaskType, sfciID, req)
                            self._sendRequest2Dispatcher(req)
                            self.rTM.updateRecoveryTask(sfcUUID, sfciID, recoveryTaskType,
                                recoveryTaskState=RECOVERY_TASK_STATE_DELETING_SFC)
                    else:
                        raise ValueError("Unknown recovery task type {0}".format(recoveryTaskType))
                elif sfciState == STATE_UNDELETED:
                    pass    # use request retry to add SFC again
            elif recoveryTaskState == RECOVERY_TASK_STATE_WAITING_TO_DELETE_SFC:
                pass    # Do nothing
            elif recoveryTaskState == RECOVERY_TASK_STATE_DELETING_SFC:
                self.logger.info("sfcState is {0}".format(sfcState))
                if sfcState == STATE_DELETED:
                    self.logger.info("sfcState == STATE_DELETED")
                    for idx, direction in enumerate(sfc.directions):
                        sfc.directions[idx]['ingress'] = None
                        sfc.directions[idx]['egress'] = None

                        source = direction['source']
                        nodeIP = source['IPv4']
                        if nodeIP == "*":
                            source["node"] = None
                        else:
                            server = self._dib.getServerByIP(nodeIP, zoneName)
                            if server == None:
                                source['node'] = None

                        destination = direction['destination']
                        nodeIP = destination['IPv4']
                        if nodeIP == "*":
                            destination["node"] = None
                        else:
                            server = self._dib.getServerByIP(nodeIP, zoneName)
                            if server == None:
                                destination['node'] = None

                    req = self.rTM.getRequestFromTask(sfcUUID, recoveryTaskType, sfciID, REQUEST_TYPE_ADD_SFC)
                    sendReqFlag = False
                    if req == None:
                        sendReqFlag = True
                    else:
                        retryNum = self._oib.getRequestRetryCnt(req.requestID)
                        # use request retry to add SFC again
                        if retryNum > MAX_RETRY_NUM:
                            sendReqFlag = True
                    self.logger.info("sendReqFlag {0}".format(sendReqFlag))
                    if sendReqFlag:
                        req = self.rG.genAddSFCRequest(sfc, zoneName)
                        self.logger.info("req is {0}".format(req))
                        self.rTM.addRequest2Task(sfcUUID, recoveryTaskType, sfciID, req)
                        self._sendRequest2Dispatcher(req)
                elif sfcState == STATE_UNDELETED:
                    self.logger.info("sfcState == STATE_UNDELETED")
                    pass
                    # Old Design: check whether exceed max retry number, then back to last state
                    # self.rTM.updateRecoveryTask(sfcUUID, sfciID, recoveryTaskType,
                    #             recoveryTaskState=RECOVERY_TASK_STATE_DELETING_SFCI)
                    # New Design: all failed requests must be processed by retry mechanism or in manual
                elif sfcState == STATE_ACTIVE:
                    self.logger.info("sfcState == STATE_ACTIVE")
                    if sfc.isAutoScaling():
                        # use scaling functions to add SFCI
                        self.rTM.updateRecoveryTask(sfcUUID, sfciID, recoveryTaskType,
                                        recoveryTaskState=RECOVERY_TASK_STATE_FINISH)
                    else:
                        sfciIDList = self.rTM.getSFCIIDListOfATask(sfcUUID, recoveryTaskType)
                        for sfciID in sfciIDList:
                            # newSFCI = self._oib.getSFCI4DB(sfciID)
                            req = self.rG.genAddSFCIRequest(sfc, SFCI(sfciID), zoneName)
                            self.rTM.addRequest2Task(sfcUUID, recoveryTaskType, sfciID, req)
                            self._sendRequest2Dispatcher(req)
                            self.rTM.updateRecoveryTask(sfcUUID, sfciID, recoveryTaskType,
                                        recoveryTaskState=RECOVERY_TASK_STATE_ADDING_SFCI)
                elif sfcState == STATE_RECOVER_MODE:
                    self.logger.info("sfcState == STATE_RECOVER_MODE")
                    pass    # Do nothing
                elif sfcState == STATE_INIT_FAILED:
                    self.logger.info("sfcState == STATE_INIT_FAILED")
                    pass    # use request retry to add SFC again
                elif sfcState == STATE_SCALING_OUT_MODE:
                    self.logger.info("sfcState == STATE_SCALING_OUT_MODE")
                    pass    # Do nothing
                else:
                    raise ValueError("Unexpected SFC state {0} during SFC recovery.".format(sfcState))
            elif recoveryTaskState == RECOVERY_TASK_STATE_ADDING_SFCI:
                if sfciState == STATE_ACTIVE:
                    self.rTM.updateRecoveryTask(sfcUUID, sfciID, recoveryTaskType,
                                    recoveryTaskState=RECOVERY_TASK_STATE_FINISH)
                    if self.rTM.isAllSFCIRecovered(sfcUUID, recoveryTaskType):
                        self._oib.updateSFCState(sfcUUID, STATE_ACTIVE)
                elif sfciState == STATE_INIT_FAILED:
                    pass
                    # Old design: retry here
                    # req = self.rTM.getRequestFromTask(sfcUUID, recoveryTaskType, sfciID, REQUEST_TYPE_ADD_SFCI)
                    # retryNum = self._oib.getRequestRetryCnt(req.requestID)
                    # self.logger.info("retryNum is {0}".format(retryNum))
                    # if retryNum > MAX_RETRY_NUM:
                    #     # newSFCI = self._oib.getSFCI4DB(sfciID)
                    #     req = self.rG.genAddSFCIRequest(sfc, SFCI(sfciID), zoneName)
                    #     self.rTM.addRequest2Task(sfcUUID, recoveryTaskType, sfciID, req)
                    #     self._sendRequest2Dispatcher(req)
                    pass
                    # New design: use regulator main program's retry function
                    # use request retry to add SFC again
                elif sfciState == STATE_IN_PROCESSING:
                    pass    # Do nothing
                elif sfciState == STATE_DELETED:
                    pass    # Do nothing
            elif recoveryTaskState == RECOVERY_TASK_STATE_FINISH:
                self.rTM.deleteRecoveryTask(sfcUUID, sfciID, recoveryTaskType)
            elif recoveryTaskState == RECOVERY_TASK_STATE_FAILED:
                pass
            else:
                raise ValueError("Unknown task state {0}".format(recoveryTaskState))

    def updateSFCIAndSFCState2RecoveryMode(self, sfciID, sfcUUID):
        # type: (SFCI, SFC) -> None
        self._oib.updateSFCState(sfcUUID, STATE_RECOVER_MODE)
        self.logger.debug("updateSFCIAndSFCState2RecoveryMode")
        self._oib.updateSFCIState(sfciID, STATE_INACTIVE)

    def isReadyToRecover(self, sfcState, sfciState):
        return ( (sfciState == STATE_ACTIVE)
                and (sfcState in [STATE_ACTIVE,
                                STATE_RECOVER_MODE]))

    def _sendCmd2Dispatcher(self, cmd):
        queueName = DISPATCHER_QUEUE
        msg = SAMMessage(MSG_TYPE_DISPATCHER_CMD, cmd)
        self._messageAgent.sendMsg(queueName, msg)

    def _sendRequest2Dispatcher(self, request):
        queueName = DISPATCHER_QUEUE
        msg = SAMMessage(MSG_TYPE_REQUEST, request)
        self._messageAgent.sendMsg(queueName, msg)
