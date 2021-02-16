#!/usr/bin/python
# -*- coding: UTF-8 -*-

import copy
import json

from sam.base.loggerConfigurator import LoggerConfigurator
# from sam.base.xibMaintainer import XInfoBaseMaintainer
from sam.ryu.uibMaintainer import *
from sam.base.socketConverter import *

# TODO: test

ENCODING_VNFID_SFCID_PATHID = "ENCODING_VNFID_SFCID_PATHID"
ENCODING_SFCID_VNFID_PATHID = "ENCODING_SFCID_VNFID_PATHID"
ENCODING_PATHID_VNFID_SFCID = "ENCODING_PATHID_VNFID_SFCID"


class UFRRIBMaintainer(UIBMaintainer):
    def __init__(self, encodingFormat=ENCODING_VNFID_SFCID_PATHID):
        super(UFRRIBMaintainer, self).__init__()
        self.groupIDSets = {}

        self.switchesUFRRTable = {}
        self.compSwitchesUFRRTable = {}

        self._sc = SocketConverter()

        self.encodingFormat = encodingFormat

        logConfigur = LoggerConfigurator(__name__, './log',
            'UFRRIBMaintainer.log', level='debug')
        self.logger = logConfigur.getLogger()

    def assignGroupID(self, dpid):
        if not self.groupIDSets.has_key(dpid):
            self.groupIDSets[dpid] = [0]
            return 0
        else:
            groupID = self.genAvailableMiniNum4List(self.groupIDSets[dpid])
            self.groupIDSets[dpid].append(groupID)
            return groupID

    def countSwitchGroupTable(self, dpid):
        count = 0
        if dpid in self.groupIDSets.keys():
            count = count + len(self.groupIDSets[dpid])
        return count

    def addSFCIUFRRFlowTableEntry(self, dpid, 
                                    sfciID, vnfID, pathID,
                                    actions, priority=0):
        if self.encodingFormat == ENCODING_VNFID_SFCID_PATHID:
            firstKey = vnfID
            secondKey = sfciID
            thirdKey = pathID
        elif self.encodingFormat == ENCODING_SFCID_VNFID_PATHID:
            firstKey = sfciID
            secondKey = vnfID
            thirdKey = pathID
        elif self.encodingFormat == ENCODING_PATHID_VNFID_SFCID:
            firstKey = pathID
            secondKey = vnfID
            thirdKey = sfciID
        else:
            raise ValueError("Unknown encoding format")

        if not self.switchesUFRRTable.has_key(dpid):
            self.switchesUFRRTable[dpid] = {}
        if not self.switchesUFRRTable[dpid].has_key(firstKey):
            self.switchesUFRRTable[dpid][firstKey] = {}
        if not self.switchesUFRRTable[dpid][firstKey].has_key(secondKey):
            self.switchesUFRRTable[dpid][firstKey][secondKey] = {}
        if not self.switchesUFRRTable[dpid][firstKey][secondKey].has_key(thirdKey):
            self.switchesUFRRTable[dpid][firstKey][secondKey][thirdKey] = {}

        self.switchesUFRRTable[dpid][firstKey][secondKey][thirdKey] \
            = {"actions":actions, "priority":priority}

    def countSwitchFlowTable(self, dpid):
        count = 0
        if dpid not in self.switchesUFRRTable.keys():
            return 0
        for firstKey in self.switchesUFRRTable[dpid].keys():
            for secondKey in self.switchesUFRRTable[dpid][firstKey].keys():
                count = count \
                    + len(self.switchesUFRRTable[dpid][firstKey][secondKey])
        return count

    def compressAllSwitchesUFRRTable(self):
        for dpid in self.switchesUFRRTable.keys():
            self.compSwitchesUFRRTable[dpid] = {}
            # compress first stage
            self.compSwitchesUFRRTable[dpid] = self.compressFirstStage(
                self.switchesUFRRTable[dpid])
            # compress second stage
            for firstKey in self.compSwitchesUFRRTable[dpid].keys():
                self.compSwitchesUFRRTable[dpid][firstKey] = \
                    self.compressSecondStage(
                        self.compSwitchesUFRRTable[dpid][firstKey])

    def compressFirstStage(self, inputSwitchTable):
        # self.logger.debug("compressFirstStage")
        # self.logger.debug("inputSwitchTable:{0}".format(
        #             json.dumps(inputSwitchTable, indent=4, default=str)
        #     ))
        switchTable = copy.deepcopy(inputSwitchTable)
        for firstKey,switchFirstKeyTable in switchTable.items():
            outputNodeID = self._findFirstKeyTableTheMostFrequentOutput(switchFirstKeyTable)
            self._mergeEntry4FirstStage(switchFirstKeyTable, outputNodeID)
        # self.logger.debug("switchTable:{0}".format(
        #     json.dumps(switchTable, indent=4, default=str)))
        return switchTable

    def _findFirstKeyTableTheMostFrequentOutput(self, switchFirstKeyTable):
        counterDict = {}
        for secondKey,switchSecondKeyTable in switchFirstKeyTable.items():
            for thirdKey, switchThirdKeyTableSubEntry in switchSecondKeyTable.items():
                # switchThirdKeyTableSubEntry is a sub entry without match fields
                actions = switchThirdKeyTableSubEntry["actions"]
                if "output nodeID" in actions.keys():
                    outputNodeID = actions["output nodeID"]
                    self._addCounterDict(counterDict, outputNodeID)
        # self.logger.debug("counterDict:{0}\n".format(
        #         json.dumps(counterDict, indent=4, default=str)
        #     ))
        # raw_input()
        if counterDict == {}:
            return None
        else:
            return self._getTheMostFrequentOutput4Dict(counterDict)

    def _getTheMostFrequentOutput4Dict(self, dictionary):
        number = max(dictionary.values())
        for key, value in dictionary.items():
            if value == number:
                return key

    def _addCounterDict(self, counterDict, outputNodeID):
        if outputNodeID not in counterDict.keys():
            counterDict[outputNodeID] = 0
        else:
            counterDict[outputNodeID] = counterDict[outputNodeID] + 1

    def _mergeEntry4FirstStage(self, switchFirstKeyTable, outputNodeID):
        # self.logger.debug("outputNodeID:{0}".format(outputNodeID))
        # self._logUFRRTable(switchFirstKeyTable)
        if outputNodeID == None:
            return
        for secondKey,switchSecondKeyTable in switchFirstKeyTable.items():
            for thirdKey, switchThirdKeyTableSubEntry in switchSecondKeyTable.items():
                # switchThirdKeyTableSubEntry is a sub entry without match fields
                actions = switchThirdKeyTableSubEntry["actions"]
                if ("output nodeID" in actions.keys()
                        and actions["output nodeID"] == outputNodeID):
                    # del switchFirstKeyTable[secondKey][thirdKey]
                    switchFirstKeyTable[secondKey].pop(thirdKey)
            # self._logUFRRTable(switchFirstKeyTable)
            # self.logger.debug("secondKey:{0}".format(secondKey))
            # raw_input()
            if switchFirstKeyTable[secondKey] == {}:
                del switchFirstKeyTable[secondKey]
        if outputNodeID != None:
            switchFirstKeyTable["*"] = {}
            switchFirstKeyTable["*"]["*"] = {"actions": {
                                            "output nodeID": outputNodeID},
                                            "priority": 16}
        # self._logUFRRTable(switchFirstKeyTable)
        # raw_input()

    def compressSecondStage(self, inputSwitchFirstKeyTable):
        switchFirstKeyTable = copy.deepcopy(inputSwitchFirstKeyTable)
        # self.logger.debug("inputSwitchFirstKeyTable:{0}".format(inputSwitchFirstKeyTable))
        # raw_input()

        # self.logger.debug("compressSecondStage")
        # self.logger.debug("switchFirstKeyTable:{0}\n".format(
        #         json.dumps(switchFirstKeyTable, indent=4, default=str)
        #     ))

        for secondKey,switchSecondKeyTable in switchFirstKeyTable.items():
            outputNodeID = self._findSecondKeyTableTheMostFrequentOutput(
                switchSecondKeyTable)
            # self.logger.debug("outputNodeID:{0}".format(outputNodeID))
            self._mergeEntry4SecondStage(switchSecondKeyTable, outputNodeID)

        # self.logger.debug("switchFirstKeyTable:{0}".format(
        #         json.dumps(switchFirstKeyTable, indent=4, default=str)
        #     ))
        # raw_input()
        return switchFirstKeyTable

    def _findSecondKeyTableTheMostFrequentOutput(self, switchSecondKeyTable):
        counterDict = {}
        for thirdKey, switchThirdKeyTableSubEntry in switchSecondKeyTable.items():
            # switchThirdKeyTableSubEntry is a sub entry without match fields
            if thirdKey == "*":
                continue
            # self.logger.debug(thirdKey)
            # self.logger.debug(switchThirdKeyTableSubEntry)
            # raw_input()
            actions = switchThirdKeyTableSubEntry["actions"]
            if "output nodeID" in actions.keys():
                outputNodeID = actions["output nodeID"]
                self._addCounterDict(counterDict, outputNodeID)
        if counterDict == {}:
            return None
        else:
            theMostFrequentOutput = max(counterDict.values())
            return theMostFrequentOutput

    def _mergeEntry4SecondStage(self, switchSecondKeyTable, outputNodeID):
        for thirdKey, switchThirdKeyTableSubEntry in switchSecondKeyTable.items():
            # switchThirdKeyTableSubEntry is a sub entry without match fields
            actions = switchThirdKeyTableSubEntry["actions"]
            if ("output nodeID" in actions.keys()
                    and actions["output nodeID"] == outputNodeID):
                del switchSecondKeyTable[thirdKey]
        if outputNodeID != None:
            switchSecondKeyTable["*"] = {"actions": {
                                            "output nodeID": outputNodeID},
                                            "priority": 24}
        if switchSecondKeyTable == {}:
            del switchSecondKeyTable
        # self.logger.debug(switchFirstKeyTable)
        # raw_input()

    def countSwitchCompressedFlowTable(self, dpid):
        count = 0
        if dpid not in self.compSwitchesUFRRTable.keys():
            return 0
        for firstKey in self.compSwitchesUFRRTable[dpid].keys():
            for secondKey in self.compSwitchesUFRRTable[dpid][firstKey].keys():
                count = count \
                    + len(self.compSwitchesUFRRTable[dpid][firstKey][secondKey])
        return count

    def verifyCompression(self):
        for dpid in self.switchesUFRRTable.keys():
            for firstKey in self.switchesUFRRTable[dpid].keys():
                for secondKey in self.switchesUFRRTable[dpid][firstKey].keys():
                    for thirdKey in \
                        self.switchesUFRRTable[dpid][firstKey][secondKey].keys():
                            self.verifyEntry(dpid, firstKey, secondKey, thirdKey)

    def verifyEntry(self, dpid, firstKey, secondKey, thirdKey):
        # {'priority': 32, 'actions': {'output port': 24}}
        subEntry = self.switchesUFRRTable[dpid][firstKey][secondKey][thirdKey]
        # print(subEntry)
        # raw_input()
        comSubEntry = self._getComSubEntry(dpid, firstKey, secondKey, thirdKey)
        self._compareSubEntry(subEntry, comSubEntry)

    def _getComSubEntry(self, dpid, firstKey, secondKey, thirdKey):
        # exactlyMatch
        try:
            return self.compSwitchesUFRRTable[dpid][firstKey][secondKey][thirdKey]
        except:
            pass

        # secondStageCompressedMatch
        try:
            return self.compSwitchesUFRRTable[dpid][firstKey][secondKey]["*"]
        except:
            pass

        # firstStageCompressedMatch
        return self.compSwitchesUFRRTable[dpid][firstKey]["*"]["*"]

    def _compareSubEntry(self, subEntry, comSubEntry):
        for actionKey in subEntry.keys():
            if (actionKey != 'priority'
                    and subEntry[actionKey] != subEntry[actionKey]):
                raise ValueError("Wrong compression. {0} and {1}".format(
                    subEntry, comSubEntry
                ))

    def _logUFRRTable(self, switchTable):
        self.logger.debug("switchUFRRTable:{0}".format(
                    json.dumps(switchTable, indent=4, default=str)
            ))
