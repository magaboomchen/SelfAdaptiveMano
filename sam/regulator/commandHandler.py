#!/usr/bin/python
# -*- coding: UTF-8 -*-

import time
import uuid
from typing import Dict, List, Tuple, Union
from logging import Logger

from sam.base.sfc import SFC, SFCI
from sam.base.command import CMD_TYPE_HANDLE_FAILURE_ABNORMAL, Command
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.messageAgent import DISPATCHER_QUEUE, MSG_TYPE_REGULATOR_CMD, \
                                    MSG_TYPE_REQUEST, MessageAgent, SAMMessage
from sam.base.path import DIRECTION0_PATHID_OFFSET, DIRECTION1_PATHID_OFFSET
from sam.base.request import REQUEST_TYPE_ADD_SFC, REQUEST_TYPE_ADD_SFCI, REQUEST_TYPE_DEL_SFC, REQUEST_TYPE_DEL_SFCI, Request
from sam.base.sfcConstant import AUTO_RECOVERY, AUTO_SCALE, STATE_ACTIVE, STATE_DELETED, STATE_IN_PROCESSING, \
                                    STATE_INACTIVE, STATE_INIT_FAILED, STATE_RECOVER_MODE, STATE_SCALING_OUT_MODE, STATE_UNDELETED
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer

RECOVERY_TASK_STATE_READY = "RECOVERY_TASK_STATE_READY"
RECOVERY_TASK_STATE_DELETING_SFCI = "RECOVERY_TASK_STATE_DELETING_SFCI"
RECOVERY_TASK_STATE_WAITING_TO_DELETE_SFC = "RECOVERY_TASK_STATE_WAITING_TO_DELETE_SFC"
RECOVERY_TASK_STATE_DELETING_SFC = "RECOVERY_TASK_STATE_DELETING_SFC"
RECOVERY_TASK_STATE_ADDING_SFCI = "RECOVERY_TASK_STATE_ADDING_SFCI"
RECOVERY_TASK_STATE_WAITING = "RECOVERY_TASK_STATE_WAITING"
RECOVERY_TASK_TYPE_SFCI = "RECOVERY_TASK_TYPE_SFCI"
RECOVERY_TASK_TYPE_SFC = "RECOVERY_TASK_TYPE_SFC"


class CommandHandler(object):
    def __init__(self, logger,  # type: Logger
                msgAgent,       # type: MessageAgent
                oib # type: OrchInfoBaseMaintainer
                ):
        self.logger = logger
        self._messageAgent = msgAgent
        self._oib = oib
        self.recoveryTaskDict = {}  # type: Dict[Tuple[SFC.sfcUUID, Union[RECOVERY_TASK_TYPE_SFCI, RECOVERY_TASK_TYPE_SFC]], Dict[SFCI.sfciID, str]]
        self.waitingRecoveryTaskDict = {}

    def handle(self, cmd):
        # type: (Command) -> None
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
        # type: (Command) -> None
        self.logger.info("Get CMD_TYPE_HANDLE_FAILURE_ABNORMAL!")
        allZoneDetectionDict = cmd.attributes["allZoneDetectionDict"]   # type: Dict[str, Dict]
        # self.updateDetectionDict()
        self._sendCmd2Dispatcher(cmd)
        for zoneName, detectionDict in allZoneDetectionDict.items():
            affectedSFCITupleList = self._getAffectedSFCIAndSFCList(
                                                        zoneName, detectionDict)
            # self.logger.debug("affectedSFCITupleList is {0}".format(affectedSFCITupleList))
            affectedSFCITupleList = self._sortInfSFCIAndSFCTupleList(affectedSFCITupleList)
            for sfci, sfc, recoveryTaskState, recoveryTaskType in affectedSFCITupleList:
                if not self.hasRecoveryTask(sfc, sfci, recoveryTaskType):
                    if self.isSFCAutoRecovery(sfc):
                        self.addRecoveryTask(sfc, sfci, recoveryTaskType, recoveryTaskState)
                    else:
                        self.addWaitingRecoveryTask(sfc, sfci, recoveryTaskType, recoveryTaskState)

    def addRecoveryTask(self, sfc, sfci, recoveryTaskType, recoveryTaskState):
        # type: (SFC, SFCI, Union[RECOVERY_TASK_TYPE_SFCI, RECOVERY_TASK_TYPE_SFC], str) -> None
        if (sfc.sfcUUID, recoveryTaskType) not in self.recoveryTaskDict.keys():
            self.recoveryTaskDict[(sfc.sfcUUID, recoveryTaskType)] = {}
        self.recoveryTaskDict[(sfc.sfcUUID, recoveryTaskType)][sfci.sfciID] = recoveryTaskState

    def addWaitingRecoveryTask(self, sfc, sfci, recoveryTaskType, recoveryTaskState):
        # type: (SFC, SFCI, Union[RECOVERY_TASK_TYPE_SFCI, RECOVERY_TASK_TYPE_SFC], str) -> None
        if (sfc.sfcUUID, recoveryTaskType) not in self.waitingRecoveryTaskDict.keys():
            self.waitingRecoveryTaskDict[(sfc.sfcUUID, recoveryTaskType)] = {}
        self.waitingRecoveryTaskDict[(sfc.sfcUUID, recoveryTaskType)][sfci.sfciID] = recoveryTaskState

    def hasRecoveryTask(self, sfc, sfci, recoveryTaskType):
        # type: (SFC, SFCI, Union[RECOVERY_TASK_TYPE_SFCI, RECOVERY_TASK_TYPE_SFC]) -> None
        if (sfc.sfcUUID, recoveryTaskType) not in self.recoveryTaskDict.keys():
            return False
        else:
            return sfci.sfciID in self.recoveryTaskDict[(sfc.sfcUUID, recoveryTaskType)].keys()

    def isSFCAutoRecovery(self, sfc):
        # type: (SFC) -> None
        return sfc.recoveryMode == AUTO_RECOVERY

    def isSFCAutoScaling(self, sfc):
        # type: (SFC) -> None
        return sfc.scalingMode == AUTO_SCALE

    def updateRecoveryTask(self, sfc, sfci, recoveryTaskType, recoveryTaskState):
        # type: (SFC, SFCI, Union[RECOVERY_TASK_TYPE_SFCI, RECOVERY_TASK_TYPE_SFC], str) -> None
        if (sfc.sfcUUID, recoveryTaskType) not in self.recoveryTaskDict.keys():
            self.recoveryTaskDict[(sfc.sfcUUID, recoveryTaskType)] = {}
        self.recoveryTaskDict[(sfc.sfcUUID, recoveryTaskType)][sfci.sfciID] = recoveryTaskState

    def deleteRecoveryTask(self, sfc, sfci, recoveryTaskType):
        # type: (SFC, SFCI, Union[RECOVERY_TASK_TYPE_SFCI, RECOVERY_TASK_TYPE_SFC]) -> None
        if (sfc.sfcUUID, recoveryTaskType) in self.recoveryTaskDict.keys():
            if sfci != None:
                del self.recoveryTaskDict[(sfc.sfcUUID, recoveryTaskType)][sfci.sfciID]
            else:
                del self.recoveryTaskDict[(sfc.sfcUUID, recoveryTaskType)]

    def isAllSFCIRecovered(self, sfcUUID, recoveryTaskType):
        # type: (uuid, Union[RECOVERY_TASK_TYPE_SFCI, RECOVERY_TASK_TYPE_SFC]) -> bool
        if len(self.recoveryTaskDict[(sfcUUID, recoveryTaskType)]) == 0:
            return True
        else:
            return False

    def isAllSFCIDeleted(self, sfcUUID):
        sfciIDList = self._oib.getSFCCorrespondingSFCIID4DB(sfcUUID)
        for sfciID in sfciIDList:
            sfciState = self._oib.getSFCIState(sfciID)
            if sfciState != STATE_DELETED:
                return False
        return True

    def processAllRecoveryTasks(self):
        self.logger.debug(" recovery task dict is {0}".format(self.recoveryTaskDict))
        for (sfcUUID, recoveryTaskType) in list(self.recoveryTaskDict.keys()):
            for sfciID, recoveryTaskState in list(self.recoveryTaskDict[(sfcUUID, recoveryTaskType)].items()):
                sfcState = self._oib.getSFCState(sfcUUID)
                sfciState = self._oib.getSFCIState(sfciID)
                sfc = self._oib.getSFC4DB(sfcUUID)  # type: SFC
                sfci = self._oib.getSFCI4DB(sfciID) # type: SFCI
                zoneName = self._oib.getSFCZone4DB(sfcUUID)
                if recoveryTaskState == RECOVERY_TASK_STATE_WAITING:
                    if self.isReadyToRecover(sfcState, sfciState):
                        self.logger.info("ready to recover.")
                        self.updateSFCIAndSFCState2RecoveryMode(sfci, sfc)
                        self.updateRecoveryTask(sfc, sfci, recoveryTaskType,
                                recoveryTaskState=RECOVERY_TASK_STATE_READY)
                elif recoveryTaskState == RECOVERY_TASK_STATE_READY:
                    req = self._genDelSFCIRequest(sfc, sfci, zoneName)
                    self._sendRequest2Dispatcher(req)
                    self.updateRecoveryTask(sfc, sfci, recoveryTaskType,
                                recoveryTaskState=RECOVERY_TASK_STATE_DELETING_SFCI)
                elif recoveryTaskState == RECOVERY_TASK_STATE_DELETING_SFCI:
                    self.logger.debug("sfciState is {0}".format(sfciState))
                    if sfciState == STATE_DELETED:
                        if recoveryTaskType == RECOVERY_TASK_TYPE_SFCI:
                            req = self._genAddSFCIRequest(sfc, sfci, zoneName)
                            self._sendRequest2Dispatcher(req)
                            self.updateRecoveryTask(sfc, sfci, recoveryTaskType,
                                    recoveryTaskState=RECOVERY_TASK_STATE_ADDING_SFCI)
                        elif recoveryTaskType == RECOVERY_TASK_TYPE_SFC:
                            self.updateRecoveryTask(sfc, sfci, recoveryTaskType,
                                    recoveryTaskState=RECOVERY_TASK_STATE_WAITING_TO_DELETE_SFC)
                            if self.isAllSFCIDeleted(sfcUUID):
                                req = self._genDelSFCRequest(sfc, zoneName)
                                self._sendRequest2Dispatcher(req)
                                self.updateRecoveryTask(sfc, sfci, recoveryTaskType,
                                    recoveryTaskState=RECOVERY_TASK_STATE_DELETING_SFC)
                        else:
                            raise ValueError("Unknown recovery task type {0}".format(recoveryTaskType))
                    elif sfciState == STATE_UNDELETED:
                        pass    # use request retry to add SFC again
                elif recoveryTaskState == RECOVERY_TASK_STATE_WAITING_TO_DELETE_SFC:
                    pass    # Do nothing
                elif recoveryTaskState == RECOVERY_TASK_STATE_DELETING_SFC:
                    if sfcState == STATE_DELETED:
                        req = self._genAddSFCRequest(sfc, zoneName)
                        self._sendRequest2Dispatcher(req)
                    elif sfcState == STATE_UNDELETED:
                        pass
                        # Old Design: check whether exceed max retry number, then back to last state
                        # self.updateRecoveryTask(sfc, sfci, recoveryTaskType,
                        #             recoveryTaskState=RECOVERY_TASK_STATE_DELETING_SFCI)
                        # New Design: all failed requests must be processed by retry mechanism or in manual
                    elif sfcState == STATE_ACTIVE:
                        if self.isSFCAutoScaling(sfc):
                            # use scaling functions to add SFCI
                            self.deleteRecoveryTask(sfc, None, recoveryTaskType)
                        else:
                            for sfciID in self.recoveryTaskDict[(sfc.sfcUUID, recoveryTaskType)]:
                                newSFCI = self._oib.getSFCI4DB(sfciID)
                                req = self._genAddSFCIRequest(sfc, newSFCI, zoneName)
                                self._sendRequest2Dispatcher(req)
                                self.updateRecoveryTask(sfc, sfci, recoveryTaskType,
                                            recoveryTaskState=RECOVERY_TASK_STATE_ADDING_SFCI)
                    elif sfcState == STATE_RECOVER_MODE:
                        pass    # Do nothing
                    elif sfcState == STATE_INIT_FAILED:
                        pass    # use request retry to add SFC again
                    elif sfcState == STATE_SCALING_OUT_MODE:
                        pass    # Do nothing
                    else:
                        raise ValueError("Unexpected SFC state {0} during SFC recovery.".format(sfcState))
                elif recoveryTaskState == RECOVERY_TASK_STATE_ADDING_SFCI:
                    if sfciState == STATE_ACTIVE:
                        self.deleteRecoveryTask(sfc, sfci, recoveryTaskType)
                        if self.isAllSFCIRecovered(sfcUUID, recoveryTaskType):
                            self._oib.updateSFCState(sfcUUID, STATE_ACTIVE)
                            self.deleteRecoveryTask(sfc, None, recoveryTaskType)
                    elif sfciState == STATE_INIT_FAILED:
                        pass    # use request retry to add SFC again
                    elif sfciState == STATE_IN_PROCESSING:
                        pass    # Do nothing
                else:
                    raise ValueError("Unknown task state {0}".format(recoveryTaskState))

    def _sendCmd2Dispatcher(self, cmd):
        queueName = DISPATCHER_QUEUE
        msg = SAMMessage(MSG_TYPE_REGULATOR_CMD, cmd)
        self._messageAgent.sendMsg(queueName, msg)

    def updateSFCIAndSFCState2RecoveryMode(self, sfci, sfc):
        # type: (SFCI, SFC) -> None
        self._oib.updateSFCState(sfc.sfcUUID, STATE_RECOVER_MODE)
        self.logger.info("updateSFCIAndSFCState2RecoveryMode")
        self._oib.updateSFCIState(sfci.sfciID, STATE_INACTIVE)

    def _getAffectedSFCIAndSFCList(self, zoneName, detectionDict):
        affectedSFCITupleList = []
        sfciTupleList = self.getAllSFCIsFromDB()
        for sfciTuple in sfciTupleList:
            # self.logger.debug("sfciTuple is {0}".format(sfciTuple))
            sfciZoneName = sfciTuple[6]
            # (SFCIID, SFC_UUID, VNFI_LIST, STATE, PICKLE, ORCHESTRATION_TIME, ZONE_NAME)
            sfcUUID = sfciTuple[1]
            sfc = self._oib.getSFC4DB(sfcUUID)  # type: SFC
            sfci = sfciTuple[4] # type: SFCI
            sfciState = self._oib.getSFCIState(sfci.sfciID)
            if sfciState != STATE_ACTIVE:
                continue
            if zoneName == sfciZoneName:
                self.logger.info("Filter influenced sfci.")
                recoveryTaskState = RECOVERY_TASK_STATE_WAITING
                influenced = False
                classifierInfluenced = False
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
                                    influenced = True
                                    if self.isNodeTheClassifier(nodeID, sfc.directions):
                                        classifierInfluenced = True
                            self.logger.debug("segPath is {0}".format(segPath))
                            for idx in range(len(segPath)-1):
                                stageNum, srcNodeID = segPath[idx]
                                dstNodeID = segPath[idx+1][1]
                                self.logger.debug("stageNum is {0}".format(stageNum))
                                linkID = (srcNodeID, dstNodeID)
                                if self.isLinkIDInDetectionDict(linkID, detectionDict):
                                    influenced = True
                if influenced:
                    if classifierInfluenced:
                        recoveryTaskType = RECOVERY_TASK_TYPE_SFC
                    else:
                        recoveryTaskType = RECOVERY_TASK_TYPE_SFCI
                    self.logger.debug("affected sfcUUID is {0}; sfciID is {1}".format(sfc.sfcUUID, sfci.sfciID))
                    affectedSFCITupleList.append((sfci, sfc, recoveryTaskState, recoveryTaskType))
            else:
                self.logger.debug("zoneName is {0}, sfciZoneName is {1}".format(zoneName, sfciZoneName))
        return affectedSFCITupleList

    def isNodeTheClassifier(self, nodeID, directions):
        # type: (int,List[Dict]) -> bool
        for direction in directions:
            ingress = direction['ingress']
            egress = direction['egress']
            if (ingress.getNodeID() == nodeID
                    or egress.getNodeID() == nodeID):
                return True
        return False

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

    def _sortInfSFCIAndSFCTupleList(self, affectedSFCITupleList):
        affectedSFCITupleList.sort(reverse=True, key=lambda x:x[1].slo.availability)
        return affectedSFCITupleList

    def _genAddSFCRequest(self, sfc, zoneName):
        req = Request(0, uuid.uuid1(), REQUEST_TYPE_ADD_SFC, 
                        attributes={
                            "sfc": sfc,
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

    def _genDelSFCIRequest(self, sfc, sfci, zoneName):
        req = Request(0, uuid.uuid1(), REQUEST_TYPE_DEL_SFCI, 
                        attributes={
                            "sfc": sfc,
                            "sfci": sfci,
                            "zone": zoneName
                    })
        return req

    def _genDelSFCRequest(self, sfc, zoneName):
        req = Request(0, uuid.uuid1(), REQUEST_TYPE_DEL_SFC, 
                        attributes={
                            "sfc": sfc,
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