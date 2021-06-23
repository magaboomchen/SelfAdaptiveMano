#!/usr/bin/python
# -*- coding: UTF-8 -*-

import copy
import json
try:
    set
except NameError:
    from sets import Set as set

from sam.base.socketConverter import *
from sam.ryu.ribMaintainerBase import RIBMaintainerBase
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.ryu.binaryTrie import BinaryTrie, BinaryTrieNode
from sam.ryu.rules import Rule

# TODO: test

ENCODING_VNFID_SFCID_PATHID = "ENCODING_VNFID_SFCID_PATHID"
ENCODING_SFCID_VNFID_PATHID = "ENCODING_SFCID_VNFID_PATHID"
ENCODING_PATHID_VNFID_SFCID = "ENCODING_PATHID_VNFID_SFCID"


class UFRRIBMaintainer(RIBMaintainerBase):
    def __init__(self, encodingFormat=ENCODING_VNFID_SFCID_PATHID):
        super(UFRRIBMaintainer, self).__init__()
        self.groupIDSets = {}
        self.switchesUFRRTable = {}
        self.compSwitchesUFRRTable = {}
        self.switchesUFRRTableInBinaryTrie = {"v4":{}, "v6":{}}
        self._sc = SocketConverter()
        self.encodingFormat = encodingFormat

        logConfigur = LoggerConfigurator(__name__, './log',
            'UFRRIBMaintainer.log', level='debug')
        self.logger = logConfigur.getLogger()

    # duplicated function in ribMaintainer
    # def assignGroupID(self, dpid):
        # if not self.groupIDSets.has_key(dpid):
        #     self.groupIDSets[dpid] = [0]
        #     return 0
        # else:
        #     groupID = self.genAvailableMiniNum4List(self.groupIDSets[dpid])
        #     self.groupIDSets[dpid].append(groupID)
        #     return groupID

    # def countSwitchGroupTable(self, dpid):
    #     count = 0
    #     if dpid in self.groupIDSets.keys():
    #         count = count + len(self.groupIDSets[dpid])
    #     return count

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

    def countSwitchCompressedFlowTableOfORTC(self, dpid, v6=False):
        if v6:
            ipVersion = "v6"
        else:
            ipVersion = "v4"
        self.logger.info(self.switchesUFRRTableInBinaryTrie["v4"].keys())
        self.logger.info(self.switchesUFRRTableInBinaryTrie[ipVersion].keys())
        bT = self.switchesUFRRTableInBinaryTrie[ipVersion][dpid]
        # count of v4 should equal to v6
        rulesNum = bT.countRules()
        self.logger.info("rules number is {0}".format(rulesNum))
        return rulesNum

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

    # Generate IPv4 address, IPv6 address
    # 1) add default null prefix rules: an default next hop
    # 2) construct a binary tree
    # 3) count rules number
    def initialBinaryTrieForAllSwitches(self, v6=False):
        if v6:
            ipVersion = "v6"
        else:
            ipVersion = "v4"
        self.switchesUFRRTableInBinaryTrie[ipVersion] = {}
        for dpid in self.switchesUFRRTable.keys():
            rules = self._generateRules(dpid, v6)
            for rule in rules:
                self.logger.debug(rule)
            bT = BinaryTrie(rules)
            self.logger.debug("Add rules to dpid: {0}".format(dpid))
            self.switchesUFRRTableInBinaryTrie[ipVersion][dpid] = bT

    def _generateRules(self, dpid, v6):
        rules = []
        for firstKey in self.switchesUFRRTable[dpid].keys():
            for secondKey in self.switchesUFRRTable[dpid][firstKey].keys():
                for thirdKey in self.switchesUFRRTable[dpid][firstKey][secondKey].keys():
                    actions = self.switchesUFRRTable[dpid][firstKey][secondKey][thirdKey]["actions"]
                    if "output nodeID" in actions.keys():
                        outputNodeID = actions["output nodeID"]
                        rule = self.__constructARule(v6, firstKey, secondKey, thirdKey, outputNodeID)
                        rules.append(rule)
                    else:
                        continue
        if v6:
            nullRule = Rule(0, 128, -1, v6=True)
        else:
            nullRule = Rule(0, 32, -1)
        rules.append(nullRule)
        return rules

    def __constructARule(self, v6, firstKey, secondKey, thirdKey, nexthop):
        if v6:
            '''
            v6:   8   40   40    40
            '''
            ipNum = (10 << (120)) + ((int(firstKey) & 0xFFFFFFFFFF) << 80) \
                + ((int(secondKey) & 0xFFFFFFFFFF) << 40) \
                + (int(thirdKey) & 0xFFFFFFFFFF)
            rule = Rule(ipNum, 128, nexthop, v6=True)
        else:
            '''
            v4    8    8    12    4
            '''
            ipNum = (10 << (24)) + ((int(firstKey) & 0xFF) << 16) \
                + ((int(secondKey) & 0xFFF) << 4) \
                + (int(thirdKey) & 0xF)
            self.logger.debug("ipNum: {0}".format(ipNum))
            rule = Rule(ipNum, 32, nexthop)
        return rule

    def compressAllSwitchesUFRRTableByORTC(self, v6=False):
        if v6:
            ipVersion = "v6"
        else:
            ipVersion = "v4"
        for dpid in self.switchesUFRRTable.keys():
            bT = self.switchesUFRRTableInBinaryTrie[ipVersion][dpid]
            self.compressByORTC(bT)

    def compressByORTC(self, bT):

        bT.levelAccess()

        print("Trie node number: {0}".format(bT.countTrieNodes()))
        self.passOne(bT)

        bT.levelAccess()
        
        print("Trie node number: {0}".format(bT.countTrieNodes()))
        self.passTwo(bT)

        bT.levelAccess()

        print("Trie node number: {0}".format(bT.countTrieNodes()))
        self.passThree(bT)

        bT.levelAccess()

    def passOne(self, bT):
        '''
        pass 1) 
        扩充trie树，保证每个节点只有0或者2个子节点。
        扩充的新节点的下一跳是最近的祖先节点的下一跳。
        leaf-pushing：只有叶子节点有下一跳，中间节点不存储下一跳（但是不需要删除中间节点的nexthop）。
        可以用pre order或者BFS实现
        '''
        root = bT.getRoot()
        self.preOrderTraversalToExpandTrie(root, bT)

    def preOrderTraversalToExpandTrie(self, node, binaryTrie):
        # Do Something with node
        if node.isOnlyHasRightChild():
            newNode = BinaryTrieNode(parent=node, depth=node.depth+1)
            node.addLeftChild(newNode)
        elif node.isOnlyHasLeftChild():
            newNode = BinaryTrieNode(parent=node, depth=node.depth+1)
            node.addRightChild(newNode)

        if node.isNextHopNone():
            node.inheritedNexthop = binaryTrie.getInherited(node)
            node.nexthopSet = set([node.inheritedNexthop])
        if node.lchild != None:
            self.preOrderTraversalToExpandTrie(node.lchild, binaryTrie)
        if node.rchild != None:
            self.preOrderTraversalToExpandTrie(node.rchild, binaryTrie)

    def passTwo(self, bT):
        '''
        pass 2)
        根据公式计算每个节点的最多下一跳
        可以用post order实现或者自底向上的遍历
        '''
        root = bT.getRoot()
        self.postOrderTraversalToFindPrevalentNextHop(root)

    def postOrderTraversalToFindPrevalentNextHop(self, node):
        if node.lchild != None:
            self.postOrderTraversalToFindPrevalentNextHop(node.lchild)
        if node.rchild != None:
            self.postOrderTraversalToFindPrevalentNextHop(node.rchild)
        # Do Something with root
        if node.hasChild():
            n1 = node.lchild
            n2 = node.rchild
            node.nexthopSet = self.sharpNodes(n1, n2)

    def sharpNodes(self, n1, n2):
        intersaction = self.intersaction(n1.nexthopSet, n2.nexthopSet)
        if self.isEmptySet(intersaction):
            return self.unionSet(n1.nexthopSet, n2.nexthopSet)
        else:
            return intersaction

    def intersaction(self, set1, set2):
        return set1.intersection(set2) 

    def isEmptySet(self, set1):
        return len(set1) == 0

    def unionSet(self, set1, set2):
        return set1.union(set2)

    def passThree(self, bT):
        '''
        pass 3)
        自顶向下，确定每个节点的nexthop
        '''
        root = bT.getRoot()
        self.preOrderTraversalToChooseNextHop(root)

    def preOrderTraversalToChooseNextHop(self, node):
        # Do Something with node
        if (not node.isRoot()) and node.isInheritedInNexthopSet():
            node.nexthopSet = set([None])
        else:
            choosedNexthop = self._choose(node.nexthopSet)
            node.nexthopSet = set([choosedNexthop])

        if node.lchild != None:
            self.preOrderTraversalToChooseNextHop(node.lchild)
        if node.rchild != None:
            self.preOrderTraversalToChooseNextHop(node.rchild)

    def _choose(self, nexthopSet):
        my_list = list(nexthopSet)
        my_list.sort()
        if my_list != []:
            return my_list[0]
        else:
            return None
