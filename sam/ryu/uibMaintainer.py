#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.xibMaintainer import *

# TODO: test

class UIBMaintainer(XInfoBaseMaintainer):
    def __init__(self, *args, **kwargs):
        super(UIBMaintainer, self).__init__(*args, **kwargs)
        self.groupIDSets = {}
        self.sfcRIB = {}
        self.sfciRIB = {}
        logConfigur = LoggerConfigurator('uibmaintainer', level='info')
        self.logger = logConfigur.getLogger()

    def assignGroupID(self, dpid):
        if not self.groupIDSets.has_key(dpid):
            self.groupIDSets[dpid] = [0]
            return 0
        else:
            groupID = self.genAvailableMiniNum4List(self.groupIDSets[dpid])
            self.groupIDSets[dpid].append(groupID)
            return groupID

    def delGroupID(self, dpid, groupID):
        self.groupIDSets[dpid].remove(groupID)

    def addSFCFlowTableEntry(self, sfcUUID, dpid, tableID, matchFields):
        if not self.sfcRIB.has_key(sfcUUID):
            self.sfcRIB[sfcUUID] = {}
        if not self.sfcRIB[sfcUUID].has_key(dpid):
            self.sfcRIB[sfcUUID][dpid] = []
        self.sfcRIB[sfcUUID][dpid].append(
            {"tableID":tableID, "match":matchFields})

    def delSFCFlowTableEntry(self, sfcUUID):
        del self.sfcRIB[sfcUUID]

    def getSFCFlowTable(self, sfcUUID):
        return self.sfcRIB[sfcUUID]

    def hasSFCFlowTable(self, sfcUUID, dpid, matchFields):
        if not self.sfcRIB.has_key(sfcUUID):
            return False
        if not self.sfcRIB[sfcUUID].has_key(dpid):
            return False
        for entry in self.sfcRIB[sfcUUID][dpid]:
            if entry["match"] == matchFields:
                return True
        else:
            return False

    def countFlowTable(self, dpid, matchFields):
        count = 0
        for sfcUUID in self.sfcRIB.keys():
            for dictItem in self.sfcRIB[sfcUUID][dpid]:
                if dictItem["match"] == matchFields:
                    count = count + 1
        return count

    def addSFCIFlowTableEntry(self, SFCIID, dpid, tableID, matchFields,
        groupID=None):
        if not self.sfciRIB.has_key(SFCIID):
            self.sfciRIB[SFCIID] = {}
        if not self.sfciRIB[SFCIID].has_key(dpid):
            self.sfciRIB[SFCIID][dpid] = []
        if groupID == None:
            self.sfciRIB[SFCIID][dpid].append(
                {"tableID":tableID, "match":matchFields})
        else:
            self.sfciRIB[SFCIID][dpid].append(
                {"tableID":tableID, "match":matchFields, "groupID":groupID})

    def delSFCIFlowTableEntry(self, SFCIID):
        del self.sfciRIB[SFCIID]

    def getSFCIFlowTable(self, SFCIID):
        return self.sfciRIB[SFCIID]

    def hasSFCIFlowTable(self, SFCIID, dpid, matchFields):
        if not self.sfciRIB.has_key(SFCIID):
            return False
        if not self.sfciRIB[SFCIID].has_key(dpid):
            return False
        self.printSFCIFlowTable(SFCIID, dpid)
        for entry in self.sfciRIB[SFCIID][dpid]:
            if entry["match"] == matchFields:
                return True
        else:
            return False

    def printSFCIFlowTable(self, SFCIID, dpid):
        for entry in self.sfciRIB[SFCIID][dpid]:
            self.logger.info(
                "entry[match]={0}".format(entry["match"])
                )