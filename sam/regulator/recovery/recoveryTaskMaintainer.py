#!/usr/bin/python
# -*- coding: UTF-8 -*-

import datetime
from uuid import UUID
from typing import Dict, List, Tuple, Union

from sam.regulator.config import RECOVERY_TASK_TIMEOUT
from sam.regulator.recovery.recoveryTask import RECOVERY_TASK_STATE_READY, \
        RECOVERY_TASK_STATE_WAITING, RecoveryTask, RECOVERY_TASK_TYPE_SFC, \
        RECOVERY_TASK_TYPE_SFCI


class RecoveryTaskMaintainer(object):
    def __init__(self):
        sfcRecoveryTaskDict = {}   # type: Dict[UUID, Dict[int, RecoveryTask]]
        sfciRecoveryTaskDict = {}  # type: Dict[UUID, Dict[int, RecoveryTask]]
        self.taskDict = {
            RECOVERY_TASK_TYPE_SFC: sfcRecoveryTaskDict,
            RECOVERY_TASK_TYPE_SFCI: sfciRecoveryTaskDict
        }

        waitingSFCRecoveryTaskDict = {}    # type: Dict[UUID, Dict[int, RecoveryTask]]
        waitingSFCIRecoveryTaskDict = {}   # type: Dict[UUID, Dict[int, RecoveryTask]]
        self.waitingTaskDict = {
            RECOVERY_TASK_TYPE_SFC: waitingSFCRecoveryTaskDict,
            RECOVERY_TASK_TYPE_SFCI: waitingSFCIRecoveryTaskDict
        }

    def addWaitingRecoveryTask(self, sfcUUID, sfciID, recoveryTaskType, recoveryTaskState):
        # type: (UUID, int, Union[RECOVERY_TASK_TYPE_SFCI, RECOVERY_TASK_TYPE_SFC], Union[RECOVERY_TASK_STATE_READY, RECOVERY_TASK_STATE_WAITING]) -> None
        if sfcUUID not in self.waitingTaskDict.keys():
            self.waitingTaskDict[recoveryTaskType][sfcUUID] = {}
        self.waitingTaskDict[sfcUUID][sfciID] = RecoveryTask(sfciID, recoveryTaskState)

    def addRecoveryTask(self, sfcUUID, sfciID, recoveryTaskType, recoveryTaskState):
        # type: (UUID, int, Union[RECOVERY_TASK_TYPE_SFCI, RECOVERY_TASK_TYPE_SFC], Union[RECOVERY_TASK_STATE_READY, RECOVERY_TASK_STATE_WAITING]) -> None
        if sfcUUID not in self.taskDict[recoveryTaskType].keys():
            self.taskDict[recoveryTaskType][sfcUUID] = {}
        self.taskDict[recoveryTaskType][sfcUUID][sfciID] = RecoveryTask(sfciID, recoveryTaskState)

    def hasRecoveryTask(self, sfcUUID, sfciID, recoveryTaskType):
        # type: (UUID, int, Union[RECOVERY_TASK_TYPE_SFCI, RECOVERY_TASK_TYPE_SFC]) -> None
        if sfcUUID not in self.taskDict[recoveryTaskType].keys():
            return False
        else:
            return sfciID in self.taskDict[recoveryTaskType][sfcUUID].keys()

    def updateRecoveryTask(self, sfcUUID, sfciID, recoveryTaskType, recoveryTaskState):
        # type: (UUID, int, Union[RECOVERY_TASK_TYPE_SFCI, RECOVERY_TASK_TYPE_SFC], Union[RECOVERY_TASK_STATE_READY, RECOVERY_TASK_STATE_WAITING]) -> None
        if sfcUUID not in self.taskDict[recoveryTaskType].keys():
            self.taskDict[recoveryTaskType][sfcUUID] = {}
        self.taskDict[recoveryTaskType][sfcUUID][sfciID] = RecoveryTask(sfciID, recoveryTaskState)

    def deleteRecoveryTask(self, sfcUUID, sfciID, recoveryTaskType):
        # type: (UUID, Union[int, None], Union[RECOVERY_TASK_TYPE_SFCI, RECOVERY_TASK_TYPE_SFC]) -> None
        if sfcUUID in self.taskDict[recoveryTaskType].keys():
            if sfciID != None:
                del self.taskDict[recoveryTaskType][sfcUUID][sfciID]
            else:
                del self.taskDict[recoveryTaskType][sfcUUID]

    def isAllSFCIRecovered(self, sfcUUID, recoveryTaskType):
        # type: (UUID, Union[RECOVERY_TASK_TYPE_SFCI, RECOVERY_TASK_TYPE_SFC]) -> bool
        if len(self.taskDict[recoveryTaskType][sfcUUID]) == 0:
            return True
        else:
            return False

    def getSFCIIDListOfATask(self, sfcUUID, recoveryTaskType):
        return list(self.taskDict[recoveryTaskType][sfcUUID].keys())

    def getRecoveryTasksTupleList(self):
        # type: (None) -> List[Tuple[UUID, str, int, str]]
        recoveryTasksTupleList = []
        for recoveryTaskType in [RECOVERY_TASK_TYPE_SFC, RECOVERY_TASK_TYPE_SFCI]:
            for sfcUUID in list(self.taskDict[recoveryTaskType].keys()):
                for sfciID, task in list(self.taskDict[recoveryTaskType][sfcUUID].items()):
                    recoveryTasksTupleList.append((sfcUUID, recoveryTaskType, sfciID, task.recoveryTaskState))
        return recoveryTasksTupleList

    def addRequest2Task(self, sfcUUID, recoveryTaskType, sfciID, req):
        reqType = req.requestType
        self.taskDict[recoveryTaskType][sfcUUID][sfciID].reqDict[reqType] = req

    def getRequestFromTask(self, sfcUUID, recoveryTaskType, sfciID, reqType):
        reqDict = self.taskDict[recoveryTaskType][sfcUUID][sfciID].reqDict
        if reqType in reqDict.keys():
            return reqDict[reqType]
        else:
            return None

    def clearRedundantTasks(self):
        recoveryTaskType = RECOVERY_TASK_TYPE_SFCI
        for sfcUUID in list(self.taskDict[recoveryTaskType].keys()):
            for sfciID, task in list(self.taskDict[recoveryTaskType][sfcUUID].items()):
                if sfcUUID in self.taskDict[RECOVERY_TASK_TYPE_SFC]:
                    task = self.taskDict[RECOVERY_TASK_TYPE_SFCI][sfcUUID][sfciID]
                    self.taskDict[RECOVERY_TASK_TYPE_SFC][sfcUUID][sfciID] = task
                    del self.taskDict[RECOVERY_TASK_TYPE_SFCI][sfcUUID][sfciID]

    def clearTimeOutTasks(self):
        for recoveryTaskType in [RECOVERY_TASK_TYPE_SFC, RECOVERY_TASK_TYPE_SFCI]:
            for sfcUUID in list(self.taskDict[recoveryTaskType].keys()):
                for sfciID, task in list(self.taskDict[recoveryTaskType][sfcUUID].items()):
                    if task.timestamp.timestamp() - datetime.datetime.now().timestamp() > RECOVERY_TASK_TIMEOUT:
                        del self.taskDict[recoveryTaskType][sfcUUID][sfciID]

    def loadWaitingTasks(self):
        for recoveryTaskType in [RECOVERY_TASK_TYPE_SFCI, RECOVERY_TASK_TYPE_SFC]:
            for sfcUUID in list(self.waitingTaskDict[recoveryTaskType].keys()):
                for sfciID, task in list(self.waitingTaskDict[recoveryTaskType][sfcUUID].items()):
                    if recoveryTaskType == RECOVERY_TASK_TYPE_SFCI:
                        if sfcUUID in self.waitingTaskDict[RECOVERY_TASK_TYPE_SFC]:
                            del self.waitingTaskDict[RECOVERY_TASK_TYPE_SFCI][sfcUUID][sfciID]
                            continue
                    if not self.hasRecoveryTask(sfcUUID, sfciID, recoveryTaskType):
                        self.addRecoveryTask(sfcUUID, sfciID, recoveryTaskType, task.recoveryTaskState)
                        del self.waitingTaskDict[recoveryTaskType][sfcUUID][sfciID]
