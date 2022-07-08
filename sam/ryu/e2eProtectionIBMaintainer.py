#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.loggerConfigurator import LoggerConfigurator
from sam.ryu.ribMaintainerBase import RIBMaintainerBase

# TODO: test

PRIMARY_ENTRY_PRIORITY = 3
LOWER_BACKUP_ENTRY_PRIORITY = 0
UPPER_BACKUP_ENTRY_PRIORITY = 5


class E2EProtectionIBMaintainer(RIBMaintainerBase):
    def __init__(self, *args, **kwargs):
        super(E2EProtectionIBMaintainer, self).__init__(*args, **kwargs)
        self.sfciDict = {}
        logConfigur = LoggerConfigurator(__name__, './log',
            'E2EProtectionIBMaintainer.log', level='debug')
        self.logger = logConfigur.getLogger()

    def addSFCIE2EPFlowTableEntry(self, sfciID, pathID,
                                dpid, tableID,
                                matchFields, actions=None, inst=None,
                                priority=LOWER_BACKUP_ENTRY_PRIORITY):
        if not (sfciID in self.sfciRIB):
            self.sfciRIB[sfciID] = {}
        if not (pathID in self.sfciRIB[sfciID]):
            self.sfciRIB[sfciID][pathID] = {}
        if not (dpid in self.sfciRIB[sfciID][pathID]):
            self.sfciRIB[sfciID][pathID][dpid] = []
        newEntry = {
                "tableID":tableID,
                "matchFields":matchFields, "priority":priority,
                "actions":actions, "inst":inst
            }
        self.sfciRIB[sfciID][pathID][dpid].append(newEntry)
        self.logger.debug("add sfci to e2ep flow table:{0}".format(newEntry))

    def hasSFCIFlowTable(self, sfciID, pathID, dpid, matchFields):
        if not (sfciID in self.sfciRIB):
            return False
        if not (pathID in self.sfciRIB[sfciID]):
            return False
        if not (dpid in self.sfciRIB[sfciID][pathID]):
            return False
        # self.printSFCIFlowTable(sfciID, dpid)
        for entry in self.sfciRIB[sfciID][pathID][dpid]:
            if entry["matchFields"] == matchFields:
                return True
        else:
            return False

    def getSFCIFlowTableEntries(self, sfciID, pathID):
        return self.sfciRIB[sfciID][pathID]

    def addSFCI(self, sfci):
        sfciID = sfci.sfciID
        if not (sfciID in self.sfciRIB):
            self.sfciDict[sfciID] = {}
        self.sfciDict[sfciID] = sfci

    def getSFCIDict(self):
        return self.sfciDict
