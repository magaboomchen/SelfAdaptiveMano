#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.xibMaintainer import XInfoBaseMaintainer
from sam.base.socketConverter import SocketConverter
from sam.ryu.conf.ryuConf import CURRENT_ENV, PICA8_ENV, MININET_ENV, \
    PICA8_AS4610_UFRR_LOGICAL_TWO_TIER_ENV, PICA8_P3922_UFRR_LOGICAL_TWO_TIER_ENV

# TODO: test


class RIBMaintainerBase(XInfoBaseMaintainer):
    def __init__(self, *args, **kwargs):
        super(RIBMaintainerBase, self).__init__(*args, **kwargs)
        self.groupIDSets = {}
        self.sfcRIB = {}
        self.sfciRIB = {}
        self.compSfciRIB = {}
        self._sc = SocketConverter()
        self.maxGroupIDDict = {"picaSwitch1": 0, "picaSwitch2": 0}
        logConfigur = LoggerConfigurator(__name__, './log',
            'RIBMaintainerBase.log', level='debug')
        self.logger = logConfigur.getLogger()

    def assignGroupID(self, dpid):
        if CURRENT_ENV == PICA8_ENV:
            self.maxGroupIDDict["picaSwitch1"] \
                = self.maxGroupIDDict["picaSwitch1"] + 1
            return self.maxGroupIDDict["picaSwitch1"]
        elif CURRENT_ENV == MININET_ENV:
            if not (dpid in self.groupIDSets):
                self.groupIDSets[dpid] = [0]
                return 0
            else:
                groupID = self.genAvailableMiniNum4List(self.groupIDSets[dpid])
                self.groupIDSets[dpid].append(groupID)
                return groupID
        elif CURRENT_ENV == PICA8_AS4610_UFRR_LOGICAL_TWO_TIER_ENV:
            if dpid in [1, 5, 6]:
                self.maxGroupIDDict["picaSwitch1"] \
                    = self.maxGroupIDDict["picaSwitch1"] + 1
                return self.maxGroupIDDict["picaSwitch1"]
            elif dpid in [2, 3, 4]:
                self.maxGroupIDDict["picaSwitch2"] \
                    = self.maxGroupIDDict["picaSwitch2"] + 1
                return self.maxGroupIDDict["picaSwitch2"]
            else:
                raise ValueError("Unknown dpid {0}".format(dpid))
        elif CURRENT_ENV == PICA8_P3922_UFRR_LOGICAL_TWO_TIER_ENV:
            self.maxGroupIDDict["picaSwitch1"] \
                = self.maxGroupIDDict["picaSwitch1"] + 1
            return self.maxGroupIDDict["picaSwitch1"]
        else:
            raise ValueError("Unknown envirnoment {0}".format(CURRENT_ENV))

    def delGroupID(self, dpid, groupID):
        if CURRENT_ENV == PICA8_ENV:
            pass
            # TODO
            self.logger.error("todo")
        elif CURRENT_ENV == MININET_ENV:
            self.groupIDSets[dpid].remove(groupID)
        elif CURRENT_ENV == PICA8_AS4610_UFRR_LOGICAL_TWO_TIER_ENV:
            pass
            # TODO
            self.logger.error("todo")
        elif CURRENT_ENV == PICA8_P3922_UFRR_LOGICAL_TWO_TIER_ENV:
            pass
            # TODO
            self.logger.error("todo")
        else:
            raise ValueError("Unknown envirnoment {0}".format(CURRENT_ENV))

    def addSFCFlowTableEntry(self, sfcUUID, dpid, tableID, matchFields):
        if not (sfcUUID in self.sfcRIB):
            self.sfcRIB[sfcUUID] = {}
        if not (dpid in self.sfcRIB[sfcUUID]):
            self.sfcRIB[sfcUUID][dpid] = []
        self.sfcRIB[sfcUUID][dpid].append(
            {"tableID":tableID, "matchFields":matchFields})

    def delSFCFlowTableEntry(self, sfcUUID):
        del self.sfcRIB[sfcUUID]

    def getSFCFlowTable(self, sfcUUID):
        return self.sfcRIB[sfcUUID]

    def hasSFCFlowTable(self, sfcUUID, dpid, matchFields):
        if not (sfcUUID in self.sfcRIB):
            return False
        if not (dpid in self.sfcRIB[sfcUUID]):
            return False
        for entry in self.sfcRIB[sfcUUID][dpid]:
            if entry["matchFields"] == matchFields:
                return True
        else:
            return False

    def countSFCRIB(self, dpid, matchFields):
        count = 0
        for sfcUUID in self.sfcRIB.keys():
            for dictItem in self.sfcRIB[sfcUUID][dpid]:
                if dictItem["matchFields"] == matchFields:
                    count = count + 1
        return count

    def countSwitchFlowTable(self, dpid):
        count = 0
        for sfciID in self.sfciRIB.keys():
            if dpid in self.sfciRIB[sfciID].keys():
                count = count + len(self.sfciRIB[sfciID][dpid])
        return count

    def countSwitchCompressedFlowTable(self, dpid, compressType):
        count = 0
        for sfciID in self.compSfciRIB[compressType].keys():
            if dpid in self.compSfciRIB[compressType][sfciID].keys():
                count = count \
                    + len(self.compSfciRIB[compressType][sfciID][dpid])
        return count

    def countSwitchGroupTable(self, dpid):
        if CURRENT_ENV == PICA8_ENV:
            return self.maxGroupIDDict["picaSwitch1"]
        elif CURRENT_ENV == MININET_ENV:
            if dpid in self.groupIDSets.keys():
                return len(self.groupIDSets[dpid])
            else:
                return 0
        elif CURRENT_ENV == PICA8_AS4610_UFRR_LOGICAL_TWO_TIER_ENV:
            if dpid in [1, 5, 6]:
                return self.maxGroupIDDict["picaSwitch1"]
            elif dpid in [2, 3, 4]:
                return self.maxGroupIDDict["picaSwitch2"]
            else:
                raise ValueError("Unknown dpid {0}".format(dpid))
        elif CURRENT_ENV == PICA8_P3922_UFRR_LOGICAL_TWO_TIER_ENV:
            return self.maxGroupIDDict["picaSwitch1"]
        else:
            raise ValueError("Unknown envirnoment {0}".format(CURRENT_ENV))

    def addSFCIFlowTableEntry(self, sfciID, dpid, tableID, matchFields,
            groupID=None, actions=None, priority=0):
        if not (sfciID in self.sfciRIB):
            self.sfciRIB[sfciID] = {}
        if not (dpid in self.sfciRIB[sfciID]):
            self.sfciRIB[sfciID][dpid] = []
        # if groupID == None:
        #     self.sfciRIB[sfciID][dpid].append(
        #         {"tableID":tableID, "matchFields":matchFields, "priority":priority})
        # else:
        #     self.sfciRIB[sfciID][dpid].append(
        #         {"tableID":tableID, "matchFields":matchFields, "groupID":groupID,
        #             "priority":priority})
        self.sfciRIB[sfciID][dpid].append(
            {
                "tableID":tableID, "matchFields":matchFields, "groupID":groupID,
                "priority":priority, "actions":actions
            }
        )

    def delSFCIFlowTableEntry(self, sfciID):
        del self.sfciRIB[sfciID]

    def getSFCIFlowTable(self, sfciID):
        return self.sfciRIB[sfciID]

    def getSFCFlowTableEntryMatchFields(self, sfcUUID, dpid, tableID):
        for entry in self.sfcRIB[sfcUUID][dpid]:
            if entry["tableID"] == tableID:
                return entry["matchFields"]
        else:
            return None

    def hasSFCIFlowTable(self, sfciID, dpid, matchFields):
        if not (sfciID in self.sfciRIB):
            return False
        if not (dpid in self.sfciRIB[sfciID]):
            return False
        # self.printSFCIFlowTable(sfciID, dpid)
        for entry in self.sfciRIB[sfciID][dpid]:
            if entry["matchFields"] == matchFields:
                return True
        else:
            return False

    def printSFCIFlowTable(self, sfciID, dpid):
        for entry in self.sfciRIB[sfciID][dpid]:
            self.logger.info("entry[match]={0}".format(entry["matchFields"]))
    
    def printUIBM(self):
        self.logger.info("printUIBM")
        self.logger.info("groupIDSets: {0}".format(self.groupIDSets))
        self.logger.info("sfcRIB: {0}".format(self.sfcRIB))
        self.logger.info("sfciRIB: {0}".format(self.sfciRIB))
