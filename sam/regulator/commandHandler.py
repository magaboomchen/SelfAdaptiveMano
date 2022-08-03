#!/usr/bin/python
# -*- coding: UTF-8 -*-

import time
import uuid

from sam.base.command import CMD_TYPE_HANDLE_FAILURE_ABNORMAL
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.messageAgent import DISPATCHER_QUEUE, MSG_TYPE_REGULATOR_CMD, MSG_TYPE_REQUEST, SAMMessage
from sam.base.path import DIRECTION0_PATHID_OFFSET, DIRECTION1_PATHID_OFFSET
from sam.base.request import REQUEST_TYPE_ADD_SFCI, REQUEST_TYPE_DEL_SFCI, Request
from sam.base.sfc import AUTO_RECOVERY, STATE_ACTIVE, STATE_DELETED, STATE_INACTIVE, STATE_RECOVER_MODE
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer

RECOVERY_TASK_STATE_READY = "RECOVERY_TASK_STATE_READY"
RECOVERY_TASK_STATE_DELETING = "RECOVERY_TASK_STATE_DELETING"
RECOVERY_TASK_STATE_ADDING = "RECOVERY_TASK_STATE_ADDING"
RECOVERY_TASK_STATE_WAITING = "RECOVERY_TASK_STATE_WAITING"


class CommandHandler(object):
    def __init__(self, logger, msgAgent, oib):
        self.logger = logger
        self._messageAgent = msgAgent
        self._oib = oib # type: OrchInfoBaseMaintainer
        self.recoveryTaskDict = {}  # dict[sfcUUID, dict[SFCIID, taskState]]

    def handle(self, cmd):
        try:
            self.logger.info("Get a command reply")
            if cmd.cmdType == CMD_TYPE_HANDLE_FAILURE_ABNORMAL:
                self.failureAbnormalHandler(cmd)
            else:
                pass
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, 
                "Regualtor command handler")
        finally:
            pass

    def failureAbnormalHandler(self, cmd):
        self.logger.info("Get CMD_TYPE_HANDLE_FAILURE_ABNORMAL!")
        allZoneDetectionDict = cmd.attributes["allZoneDetectionDict"]
        self._sendCmd2Dispatcher(cmd)
        for zoneName, detectionDict in allZoneDetectionDict.items():
            infSFCIAndSFCTupleList = self._getInfluencedSFCIAndSFCList(
                                                        zoneName, detectionDict)
            self.logger.debug("infSFCIAndSFCTupleList is {0}".format(infSFCIAndSFCTupleList))
            infSFCIAndSFCTupleList = self._sortInfSFCIAndSFCTupleList(infSFCIAndSFCTupleList)
            for sfci, sfc, recoveryTaskState in infSFCIAndSFCTupleList:
                if not self.hasRecoveryTask(sfc, sfci) and self.isSFCAutoRecovery(sfc):
                    self.addRecoveryTask(sfc, sfci, recoveryTaskState)

    def addRecoveryTask(self, sfc, sfci, recoveryTaskState):
        if sfc.sfcUUID not in self.recoveryTaskDict.keys():
            self.recoveryTaskDict[sfc.sfcUUID] = {}
        self.recoveryTaskDict[sfc.sfcUUID][sfci.sfciID] = recoveryTaskState

    def hasRecoveryTask(self, sfc, sfci):
        if sfc.sfcUUID not in self.recoveryTaskDict.keys():
            return False
        else:
            return sfci.sfciID in self.recoveryTaskDict[sfc.sfcUUID].keys()

    def isSFCAutoRecovery(self, sfc):
        return sfc.recoveryMode == AUTO_RECOVERY

    def updateRecoveryTask(self, sfc, sfci, recoveryTaskState):
        if sfc.sfcUUID not in self.recoveryTaskDict.keys():
            self.recoveryTaskDict[sfc.sfcUUID] = {}
        self.recoveryTaskDict[sfc.sfcUUID][sfci.sfciID] = recoveryTaskState

    def deleteRecoveryTask(self, sfc, sfci):
        if sfc.sfcUUID in self.recoveryTaskDict.keys():
            del self.recoveryTaskDict[sfc.sfcUUID][sfci.sfciID]

    def isAllSFCIRecovered(self, sfcUUID):
        if len(self.recoveryTaskDict[sfcUUID]) == 0:
            return True
        else:
            return False

    def processAllRecoveryTasks(self):
        self.logger.debug(" recovery task dict is {0}".format(self.recoveryTaskDict))
        time.sleep(1)
        for sfcUUID in list(self.recoveryTaskDict.keys()):
            for sfciID, recoveryTaskState in list(self.recoveryTaskDict[sfcUUID].items()):
                sfcState = self._oib.getSFCState(sfcUUID)
                sfciState = self._oib.getSFCIState(sfciID)
                sfc = self._oib.getSFC4DB(sfcUUID)
                sfci = self._oib.getSFCI4DB(sfciID)
                if recoveryTaskState == RECOVERY_TASK_STATE_WAITING:
                    if self.isReadyToRecover(sfcState, sfciState):
                        self.logger.info("ready to recover.")
                        self.updateSFCIAndSFCState2RecoveryMode(sfci, sfc)
                        self.updateRecoveryTask(sfc, sfci, 
                                recoveryTaskState=RECOVERY_TASK_STATE_READY)
                elif recoveryTaskState == RECOVERY_TASK_STATE_READY:
                    zoneName = self._oib.getSFCZone4DB(sfcUUID)
                    req = self._genDelSFCIRequest(sfc, sfci, zoneName)
                    self._sendRequest2Dispatcher(req)
                    self.updateRecoveryTask(sfc, sfci, 
                                recoveryTaskState=RECOVERY_TASK_STATE_DELETING)
                elif recoveryTaskState == RECOVERY_TASK_STATE_DELETING:
                    if sfciState == STATE_DELETED:
                        zoneName = self._oib.getSFCZone4DB(sfcUUID)
                        req = self._genAddSFCIRequest(sfc, sfci, zoneName)
                        self._sendRequest2Dispatcher(req)
                        self.updateRecoveryTask(sfc, sfci, 
                                    recoveryTaskState=RECOVERY_TASK_STATE_ADDING)
                    self.logger.debug("sfciState is {0}".format(sfciState))
                elif recoveryTaskState == RECOVERY_TASK_STATE_ADDING:
                    if sfciState == STATE_ACTIVE:
                        self.deleteRecoveryTask(sfc, sfci)
                        if self.isAllSFCIRecovered(sfcUUID):
                            self._oib.updateSFCState(sfcUUID, STATE_ACTIVE)
                else:
                    raise ValueError("Unknown task state {0}".format(recoveryTaskState))

    def _sendCmd2Dispatcher(self, cmd):
        queueName = DISPATCHER_QUEUE
        msg = SAMMessage(MSG_TYPE_REGULATOR_CMD, cmd)
        self._messageAgent.sendMsg(queueName, msg)

    def updateSFCIAndSFCState2RecoveryMode(self, sfci, sfc):
        self._oib.updateSFCState(sfc.sfcUUID, STATE_RECOVER_MODE)
        self.logger.info("updateSFCIAndSFCState2RecoveryMode")
        self._oib.updateSFCIState(sfci.sfciID, STATE_INACTIVE)

    def _getInfluencedSFCIAndSFCList(self, zoneName, detectionDict):
        infSFCIAndSFCTupleList = []
        sfciTupleList = self.getAllSFCIsFromDB()
        for sfciTuple in sfciTupleList:
            self.logger.info("sfciTuple is {0}".format(sfciTuple))
            sfciZoneName = sfciTuple[6]
            if zoneName == sfciZoneName:
                self.logger.info("Filter influenced sfci.")
                # (SFCIID, SFC_UUID, VNFI_LIST, STATE, PICKLE, ORCHESTRATION_TIME, ZONE_NAME)
                sfcUUID = sfciTuple[1]
                sfc = self._oib.getSFC4DB(sfcUUID)
                sfcState = self._oib.getSFCState(sfcUUID)
                sfciState = sfciTuple[3]
                # if self.isReadyToRecover(sfcState, sfciState):
                #     recoveryTaskState = RECOVERY_TASK_STATE_WAITING
                # else:
                #     recoveryTaskState = RECOVERY_TASK_STATE_READY
                recoveryTaskState = RECOVERY_TASK_STATE_WAITING
                sfci = sfciTuple[4]
                for pathIDOffset in [DIRECTION0_PATHID_OFFSET, DIRECTION1_PATHID_OFFSET]:
                    fPathList = []
                    if pathIDOffset in sfci.forwardingPathSet.primaryForwardingPath:
                        fPathList.append(sfci.forwardingPathSet.primaryForwardingPath[pathIDOffset])
                    if pathIDOffset in sfci.forwardingPathSet.backupForwardingPath:
                        fPathList.append(sfci.forwardingPathSet.backupForwardingPath[pathIDOffset])
                    for forwardingPath in fPathList:
                        for segPath in forwardingPath:
                            for stageNum, nodeID in segPath:
                                if self.isNodeIDInDetectionDict(nodeID, detectionDict):
                                    infSFCIAndSFCTupleList.append((sfci, sfc, recoveryTaskState))
                            self.logger.info("segPath is {0}".format(segPath))
                            for stageNum, nodeID in segPath[:-2]:
                                self.logger.info("stageNum is {0}".format(stageNum))
                                linkID = (nodeID, segPath[stageNum][1])
                                if self.isLinkIDInDetectionDict(linkID, detectionDict):
                                    infSFCIAndSFCTupleList.append((sfci, sfc, recoveryTaskState))
            else:
                self.logger.debug("zoneName is {0}, sfciZoneName is {1}".format(zoneName, sfciZoneName))
        return infSFCIAndSFCTupleList

    def isReadyToRecover(self, sfcState, sfciState):
        return ( (sfciState == STATE_ACTIVE)
                and (sfcState in [STATE_ACTIVE,
                                STATE_RECOVER_MODE]))

    def isNodeIDInDetectionDict(self, nodeID, detectionDict):
        keyList = ["failure", "abnormal"]
        for key in keyList:
            for listType in ["switchIDList", "serverIDList"]:
                idList = detectionDict[key][listType]
                if nodeID in idList:
                    return True
        return False

    def isLinkIDInDetectionDict(self, linkID, detectionDict):
        keyList = ["failure", "abnormal"]
        for key in keyList:
            for listType in ["linkIDList", "serverIDList"]:
                idList = detectionDict[key][listType]
                if linkID in idList:
                    return True
                reversedLinkID = (linkID[1], linkID[0])
                if reversedLinkID in idList:
                    return True
        return False

    def _sortInfSFCIAndSFCTupleList(self, infSFCIAndSFCTupleList):
        infSFCIAndSFCTupleList.sort(reverse=True, key=lambda x:x[1].slo.availability)
        return infSFCIAndSFCTupleList

    def _genDelSFCIRequest(self, sfc, sfci, zoneName):
        req = Request(0, uuid.uuid1(), REQUEST_TYPE_DEL_SFCI, 
                        attributes={
                            "sfc": sfc,
                            "sfci": sfci,
                            "zone": zoneName
                    })
        return req

    def _genAddSFCIRequest(self, sfc, sfci, zoneName):
        req = Request(0, uuid.uuid1(), REQUEST_TYPE_ADD_SFCI, 
                        attributes={
                            "sfc": sfc,
                            "sfci": sfci,
                            "zone": zoneName
                    })
        return req

    def _sendRequest2Dispatcher(self, request):
        queueName = DISPATCHER_QUEUE
        msg = SAMMessage(MSG_TYPE_REQUEST, request)
        self._messageAgent.sendMsg(queueName, msg)

    def getAllSFCIsFromDB(self):
        sfciTupleList = self._oib.getAllSFCI()
        return sfciTupleList

    def getAllSFCsFromDB(self):
        sfcTupleList = self._oib.getAllSFC()
        return sfcTupleList