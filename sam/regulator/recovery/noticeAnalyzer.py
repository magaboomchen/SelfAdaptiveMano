#!/usr/bin/python
# -*- coding: UTF-8 -*-

from typing import Dict, List, Tuple
from uuid import UUID

from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.sfc import SFC, SFCI
from sam.base.path import DIRECTION0_PATHID_OFFSET, DIRECTION1_PATHID_OFFSET
from sam.base.sfcConstant import STATE_ACTIVE
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer
from sam.regulator.recovery.recoveryTask import RECOVERY_TASK_STATE_FAILED, RECOVERY_TASK_STATE_WAITING, RECOVERY_TASK_TYPE_SFC, RECOVERY_TASK_TYPE_SFCI
from sam.regulator.recovery.recoveryTaskMaintainer import RecoveryTaskMaintainer


class NoticeAnalyzer(object):
    def __init__(self, oib, rTM):
        # type: (OrchInfoBaseMaintainer, RecoveryTaskMaintainer) -> None
        self._oib = oib
        self.rTM = rTM
        logConfigur = LoggerConfigurator(__name__, './log',
            'NoticeAnalyzer.log',
            level='debug')
        self.logger = logConfigur.getLogger()

    def getAffectedSFCITupleList(self, allZoneDetectionDict):
        # type: (Dict) -> List[Tuple[int, SFC, str, str]]
        affectedSFCITupleList = []
        for zoneName, detectionDict in allZoneDetectionDict.items():
            atList = self._getAffectedSFCIAndSFCList(zoneName, detectionDict)
            affectedSFCITupleList.extend(atList)
            # self.logger.debug("affectedSFCITupleList is {0}".format(affectedSFCITupleList))
        affectedSFCITupleList = self._sortInfSFCIAndSFCTupleList(affectedSFCITupleList)
        return affectedSFCITupleList

    def _getAffectedSFCIAndSFCList(self, zoneName, detectionDict):
        self.logger.info("detectionDict is {0}".format(detectionDict))
        affectedSFCITupleList = []
        sfciTupleList = self.getAllSFCIsFromDB()
        # self.logger.debug("sfciTupleList is {0}".format(sfciTupleList))
        for sfciTuple in sfciTupleList:
            # self.logger.debug("sfciTuple is {0}".format(sfciTuple))
            sfciZoneName = sfciTuple[6]
            # (SFCIID, SFC_UUID, VNFI_LIST, STATE, PICKLE, ORCHESTRATION_TIME, ZONE_NAME)
            sfcUUID = sfciTuple[1]
            sfc = self._oib.getSFC4DB(sfcUUID)  # type: SFC
            sfci = sfciTuple[4] # type: SFCI
            sfciID = sfci.sfciID
            sfciState = self._oib.getSFCIState(sfci.sfciID)
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
                                        self.logger.debug("nodeID is {0}, ingressID is {1}, egressID is {2}".format(
                                                            nodeID, sfc.directions[0]['ingress'].getNodeID(),
                                                            sfc.directions[0]['egress'].getNodeID()
                                                            ))
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
                    if sfciState != STATE_ACTIVE:
                        if classifierInfluenced:
                            interestTaskType = RECOVERY_TASK_TYPE_SFCI
                        else:
                            interestTaskType = recoveryTaskType
                        taskState = self.rTM.getRecoveryTaskState(sfcUUID, interestTaskType, sfciID)
                        self.logger.info("taskState is {0}".format(taskState))
                        if taskState == RECOVERY_TASK_STATE_FAILED:
                            pass
                        else:
                            continue
                    self.logger.debug("affected sfcUUID is {0}; " \
                                        "sfciID is {1}; " \
                                        "recoveryTaskType is {2}" \
                                        " ".format(sfc.sfcUUID, sfci.sfciID, recoveryTaskType))
                    affectedSFCITupleList.append((sfci.sfciID, sfc, recoveryTaskState, recoveryTaskType))
            else:
                self.logger.debug("zoneName is {0}, sfciZoneName is {1}".format(zoneName, sfciZoneName))
        return affectedSFCITupleList

    def _sortInfSFCIAndSFCTupleList(self, affectedSFCITupleList):
        affectedSFCITupleList.sort(reverse=True, key=lambda x:x[1].slo.availability)
        return affectedSFCITupleList

    def isNodeTheClassifier(self, nodeID, directions):
        # type: (int, List[Dict]) -> bool
        for direction in directions:
            ingress = direction['ingress']
            egress = direction['egress']
            if (ingress.getNodeID() == nodeID
                    or egress.getNodeID() == nodeID):
                return True
        return False

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

    def getAllSFCIsFromDB(self):
        sfciTupleList = self._oib.getAllSFCI()
        return sfciTupleList

    def getAllSFCsFromDB(self):
        sfcTupleList = self._oib.getAllSFC()
        return sfcTupleList