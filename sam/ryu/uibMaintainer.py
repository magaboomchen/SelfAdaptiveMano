#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.xibMaintainer import XInfoBaseMaintainer

# TODO: test


class UIBMaintainer(XInfoBaseMaintainer):
    def __init__(self, *args, **kwargs):
        super(UIBMaintainer, self).__init__(*args, **kwargs)
        self.groupIDSets = {}
        self.sfcRIB = {}
        self.sfciRIB = {}
        logConfigur = LoggerConfigurator(__name__, './log',
            'UIBMaintainer.log', level='debug')
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

    def addSFCIFlowTableEntry(self, sfciID, dpid, tableID, matchFields,
        groupID=None):
        if not self.sfciRIB.has_key(sfciID):
            self.sfciRIB[sfciID] = {}
        if not self.sfciRIB[sfciID].has_key(dpid):
            self.sfciRIB[sfciID][dpid] = []
        if groupID == None:
            self.sfciRIB[sfciID][dpid].append(
                {"tableID":tableID, "match":matchFields})
        else:
            self.sfciRIB[sfciID][dpid].append(
                {"tableID":tableID, "match":matchFields, "groupID":groupID})

    def delSFCIFlowTableEntry(self, sfciID):
        del self.sfciRIB[sfciID]

    def getSFCIFlowTable(self, sfciID):
        return self.sfciRIB[sfciID]

    def getSFCFlowTableEntryMatchFields(self, sfcUUID, dpid, tableID):
        for entry in self.sfcRIB[sfcUUID][dpid]:
            if entry["tableID"] == tableID:
                return entry["match"]
        else:
            return None

    def hasSFCIFlowTable(self, sfciID, dpid, matchFields):
        if not self.sfciRIB.has_key(sfciID):
            return False
        if not self.sfciRIB[sfciID].has_key(dpid):
            return False
        # self.printSFCIFlowTable(sfciID, dpid)
        for entry in self.sfciRIB[sfciID][dpid]:
            if entry["match"] == matchFields:
                return True
        else:
            return False

    def printSFCIFlowTable(self, sfciID, dpid):
        for entry in self.sfciRIB[sfciID][dpid]:
            self.logger.info(
                "entry[match]={0}".format(entry["match"])
                )
    
    def printUIBM(self):
        self.logger.info("printUIBM")
        self.logger.info("groupIDSets: {0}".format(self.groupIDSets))
        self.logger.info("sfcRIB: {0}".format(self.sfcRIB))
        self.logger.info("sfciRIB: {0}".format(self.sfciRIB))
