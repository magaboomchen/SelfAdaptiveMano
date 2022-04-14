#!/usr/bin/python
# -*- coding: UTF-8 -*-

import copy
import json

from sam.base.loggerConfigurator import LoggerConfigurator
from sam.ryu.ribMaintainerBase import RIBMaintainerBase
from sam.base.socketConverter import SocketConverter, BCAST_MAC

# TODO: test

LOWER_BACKUP_ENTRY_PRIORITY = 0
UPPER_BACKUP_ENTRY_PRIORITY = 5


class PSFCIBMaintainer(RIBMaintainerBase):
    def __init__(self):
        super(PSFCIBMaintainer, self).__init__()
        self.sfciDict = {}
        logConfigur = LoggerConfigurator(__name__, './log',
            'PSFCIBMaintainer.log', level='debug')
        self.logger = logConfigur.getLogger()

    def addSFCIPSFCFlowTableEntry(self, sfciID, backupPathKey, dpid, tableID,
                                matchFields, actions=None, inst=None,
                                priority=LOWER_BACKUP_ENTRY_PRIORITY):
        if not self.sfciRIB.has_key(sfciID):
            self.sfciRIB[sfciID] = {}
        if not self.sfciRIB[sfciID].has_key(backupPathKey):
            self.sfciRIB[sfciID][backupPathKey] = {}
        if not self.sfciRIB[sfciID][backupPathKey].has_key(dpid):
            self.sfciRIB[sfciID][backupPathKey][dpid] = []
        self.sfciRIB[sfciID][backupPathKey][dpid].append(
            {
                "tableID":tableID,
                "matchFields":matchFields, "priority":priority,
                "actions":actions, "inst":inst
            }
        )

    def getSFCIFlowTableEntries(self, sfciID, backupPathKey):
        return self.sfciRIB[sfciID][backupPathKey]

    def addSFCI(self, sfci):
        sfciID = sfci.sfciID
        if not self.sfciRIB.has_key(sfciID):
            self.sfciDict[sfciID] = {}
        self.sfciDict[sfciID] = sfci

    def getSFCIDict(self):
        return self.sfciDict
