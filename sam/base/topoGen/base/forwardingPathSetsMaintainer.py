#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
import pickle
import base64
import numpy as np
import pandas as pd

from sam.base.path import *
from sam.serverController.serverManager import *
from sam.orchestration.algorithms.mMLBSFC.mMLBSFC import *
from sam.orchestration.algorithms.base.failureScenario import *
from sam.base.loggerConfigurator import LoggerConfigurator


class ForwardingPathSetsMaintainer(MMLBSFC):
    def __init__(self, forwardingPathSetsDict, failureType):
        self.forwardingPathSetsDict = copy.deepcopy(forwardingPathSetsDict)
        self.failureType = failureType

        logConfigur = LoggerConfigurator(__name__, './log',
            'forwardingPathSetsMaintainer.log', level='debug')
        self.logger = logConfigur.getLogger()

        # self._printFPSD()

    def _printFPSD(self):
        self.logger.debug("forwardingPathSetsDict: {0}\n_____".format(
            self.forwardingPathSetsDict))
        raw_input()

    def getPrimaryForwardingPath(self, rIndex):
        return self.forwardingPathSetsDict[rIndex].primaryForwardingPath[1]

    def getForwardingPathDictInScenario(self, scenario):
        self.forwardingPathDict = {}
        self.failureElementList = scenario.getElementsList()
        for rIndex, forwardingPathSet in self.forwardingPathSetsDict.items():
            self.primaryForwardingPath = forwardingPathSet.primaryForwardingPath[1]
            self.backupForwardingPaths = forwardingPathSet.backupForwardingPath[1]
            self.mappingType = forwardingPathSet.mappingType
            if not self._isForwardingPathAffectedByFailure(self.primaryForwardingPath):
                self.forwardingPathDict[rIndex] = self.primaryForwardingPath
            else:
                if self.mappingType == MAPPING_TYPE_E2EP:
                    self._getE2EPForwardingPathDict(rIndex)
                elif self.mappingType == MAPPING_TYPE_UFRR:
                    self._getUFRRForwardingPathDict(rIndex)
                elif self.mappingType == MAPPING_TYPE_NOTVIA_PSFC:
                    self._getNotViaPSFCForwardingPathDict(rIndex)
                else:
                    raise ValueError(
                        "Unknown mapping type:{0}".format(
                            self.mappingType))
        return self.forwardingPathDict

    def _getE2EPForwardingPathDict(self, rIndex):
        for key, backupForwardingPath in self.backupForwardingPaths.items():
            # self.logger.debug(
            #     "primaryForwardingPath:{0}\nfailureList:{1}\n"
            #     "key:{2}\npath:{3}".format(
            #         self.primaryForwardingPath, self.failureElementList, 
            #         key, backupForwardingPath))
            if self._isE2EBackupForwardingPathUnderFailure(key,
                                                        backupForwardingPath):
                self.forwardingPathDict[rIndex] = copy.deepcopy(backupForwardingPath)
                # self.logger.debug("Valid Backup backupForwardingPath")
                break
            else:
                if self.failureType == "link":
                    if (self.failureElementList[0].srcID > 10000 
                            or self.failureElementList[0].dstID > 10000):
                        continue
                self.logger.warning(
                    "InValid Backup Path for rIndex:{0}\n"
                    "under failure:{1}\n"
                    "primaryForwardingPath:{2}\n"
                    "backupForwardingPath:{3}".format(
                        rIndex, self.failureElementList,
                            self.primaryForwardingPath,
                            backupForwardingPath))
        else:
            # self.logger.debug(
            #     "backupForwardingPaths:{0}".format(
            #         self.backupForwardingPaths))
            # self.logger.debug(
            #     "primaryForwardingPath:{0}\nfailureList:{1}\n"
            #     "key:{2}\npath:{3}".format(
            #         self.primaryForwardingPath, self.failureElementList, 
            #         key, backupForwardingPath))
            self.forwardingPathDict[rIndex] = [[]]

    def _getUFRRForwardingPathDict(self, rIndex):
        unaffectedForwardingPath \
            = self._getUnaffectedPartOfPrimaryForwardingPath(
                rIndex, self.primaryForwardingPath)
        # self.logger.debug("unaffected part:{0}".format(
        #     unaffectedForwardingPath))
        for key, backupForwardingPath in self.backupForwardingPaths.items():
            # self.logger.debug(
            #     "primaryForwardingPath:{0}\nfailureList:{1}\n"
            #     "key:{2}\npath:{3}".format(
            #         self.primaryForwardingPath, self.failureElementList, 
            #         key, backupForwardingPath))
            if self._isBackupForwardingPathUnderFailure(key):
                self.forwardingPathDict[rIndex] \
                    = copy.deepcopy(self._mergePath2UFP(backupForwardingPath,
                                            unaffectedForwardingPath))
                # self.logger.debug("unaffected part:{0}".format(
                #     unaffectedForwardingPath))
                # self.logger.debug("backup backupForwardingPath:{0}".format(
                #     backupForwardingPath))
                # self.logger.debug(
                #     "merged forwarding backupForwardingPath:{0}".format(
                #         self.forwardingPathDict[rIndex]))
                # raw_input()
                break 
        else:
            self.logger.warning(
                "primaryForwardingPath:{0}\nbackupForwardingPaths:{1}\nfailureList:{2}\n".format(
                    self.primaryForwardingPath, 
                    self.backupForwardingPaths,
                    self.failureElementList))
            self.forwardingPathDict[rIndex] = [[]]

    def _getNotViaPSFCForwardingPathDict(self, rIndex):
        # self._printFPSD()
        self._updateForwardingPathByNotVia(rIndex)
        # self._printFPSD()
        self._updateForwardingPathByPSFC(rIndex)
        # self._printFPSD()

    def _updateForwardingPathByNotVia(self, rIndex):
        self.logger.debug("rIndex:{0}".format(rIndex))
        self.logger.debug("primaryForwardingPath:{0}".format(
                            self.primaryForwardingPath))
        self.logger.debug("failure element list:{0}".format(
                            self.failureElementList))

        if self.failureType == "link":
            if (self.failureElementList[0].srcID >= SERVERID_OFFSET 
                    or self.failureElementList[0].dstID >= SERVERID_OFFSET):
                self.logger.warning("notVia can't protect link connecting a server!")
                return 

            newForwardingPath = []
            for segPath in self.primaryForwardingPath:
                # self.logger.debug("segPath:{0}".format(segPath))
                newSegPath = copy.deepcopy([segPath[0]])
                if len(segPath) >= 4:
                    mergeFlag = False
                    mergeSwitchID = -1
                    for layerNodeIndex in range(1, len(segPath)-1):
                        layerNode = segPath[layerNodeIndex]
                        (layerNum, nodeID) = layerNode
                        nextLayerNode = segPath[layerNodeIndex+1]
                        (layerNum, nextNodeID) = nextLayerNode

                        if (layerNode[1] != mergeSwitchID
                                and mergeFlag):
                            continue
                        elif (layerNode[1] == mergeSwitchID
                                and mergeFlag):
                            mergeFlag = False
                            continue
                        else:
                            pass

                        if layerNodeIndex == len(segPath) - 2:
                            newSegPath.append((layerNum, nodeID))
                            break

                        linkID = (layerNode[1], nextLayerNode[1])
                        reverseLinkID = (nextLayerNode[1], layerNode[1])
                        layerLinkID = (layerNode, nextLayerNode)
                        isFailureLink = (self._isLinkIDInFailureElementList(linkID)
                                or self._isLinkIDInFailureElementList(reverseLinkID))
                        hasNotViaBackupPath = self._hasNotViaByPassPath(layerLinkID)

                        # self.logger.debug("linkID:{0}".format(linkID))
                        # self.logger.debug("is failure link? {0}".format(isFailureLink))
                        # self.logger.debug("layerLinkID:{0}".format(layerLinkID))
                        # self.logger.debug("has bypass path? {0}".format(hasNotViaBackupPath))
                        # raw_input()

                        if (isFailureLink and hasNotViaBackupPath):
                            byPassPath = self._getNotViaByPassPath(layerLinkID)
                            newSegPath.extend(byPassPath[0])
                            mergeSwitchID = byPassPath[0][-1][1]
                            # self.logger.debug("mergeSwitchID:{0}".format(
                            #     mergeSwitchID))
                            # raw_input()
                            mergeFlag = True
                        else:
                            newSegPath.append((layerNum, nodeID))

                        if (isFailureLink == True and hasNotViaBackupPath == False):
                            self.logger.warning("notVia can't protect this link!")
                            # self.logger.warning("isFailureLink:{0}, hasNotViaBackupPath:{1}".format(
                            #                         isFailureLink, hasNotViaBackupPath))
                            return
 
                    newSegPath.extend(segPath[-1:])
                else:
                    newSegPath = copy.deepcopy(segPath)
                # self.logger.debug("newSegPath:{0}".format(newSegPath))
                newForwardingPath.append(newSegPath)

            # self.logger.debug("primaryForwardingPath:{0}".format(
            #         self.primaryForwardingPath))
            self.logger.debug("notVia can protect this link {0}"
                                "newForwardingPath:{1}".format(
                                    self.failureElementList, newForwardingPath))
            # raw_input()

            self.forwardingPathDict[rIndex] = newForwardingPath
            # return newForwardingPath

        elif self.failureType == "node":
            raise ValueError("Please implement failureType 'link'")
        else:
            raise ValueError(
                "Unknown failureType:{0}".format(
                    self.failureType))

    def _hasNotViaByPassPath(self, linkID):
        for key, backupForwardingPath in self.backupForwardingPaths.items():
            if self._isPSFCBypassPath(key):
                continue

            keyDict = self._parseBackupForwardingPathKey(key)
            if self._isByPassPathNodeProtection(key):
                failureLayerNodeID = keyDict["failureLayerNodeID"]
                repairLayerSwitchID = keyDict["repairLayerSwitchID"]
                mergeLayerSwitchID = keyDict["mergeLayerSwitchID"]

                if (linkID[0] == repairLayerSwitchID
                        and linkID[1] == failureLayerNodeID):
                    return True
            else:
                raise ValueError("Unsupport protection")
        else:
            return False

    def _isByPassPathNodeProtection(self, key):
        keyDict = self._parseBackupForwardingPathKey(key)
        if "failureLayerNodeID" in keyDict.keys():
            return True
        else:
            return False

    def _getNotViaByPassPath(self, linkID):
        for key, backupForwardingPath in self.backupForwardingPaths.items():
            if self._isPSFCBypassPath(key):
                continue

            keyDict = self._parseBackupForwardingPathKey(key)
            if self._isByPassPathNodeProtection(key):
                failureLayerNodeID = keyDict["failureLayerNodeID"]
                repairLayerSwitchID = keyDict["repairLayerSwitchID"]
                mergeLayerSwitchID = keyDict["mergeLayerSwitchID"]

                if (linkID[0] == repairLayerSwitchID
                        and linkID[1] == failureLayerNodeID):
                    return backupForwardingPath
            else:
                raise ValueError("Unsupport protection")
        else:
            return False

    def _isPSFCBypassPath(self, key):
        keyDict = self._parseBackupForwardingPathKey(key)
        if 'failureNPoPID' in keyDict.keys():
            return True
        else:
            return False

    def _updateForwardingPathByPSFC(self, rIndex):
        updateFlag = False

        originPrimaryFP = self.getPrimaryForwardingPath(rIndex)

        for key, backupForwardingPath in self.backupForwardingPaths.items():
            # self.logger.debug(
            #     "primaryForwardingPath:{0}\nfailureList:{1}\n"
            #     "key:{2}\npath:{3}".format(
            #         self.primaryForwardingPath, self.failureElementList, 
            #         key, backupForwardingPath))
            if not self._isPSFCBypassPath(key):
                continue
            if self._isBypassPathUnderFailure(key):
                if not self.forwardingPathDict.has_key(rIndex):
                    updateFlag = True
                    self.logger.debug("Use pSFC partial rerouting path, rIndex:{0}".format(rIndex))
                    originPrimaryFP \
                        = copy.deepcopy(self._mergePSFCBypassPath2ForwardingPath(
                                            key, backupForwardingPath, originPrimaryFP
                                            ))
                else:
                    self.logger.debug("Use notVia path, rIndex:{0}".format(rIndex))

        if updateFlag == True:
            self.forwardingPathDict[rIndex] = originPrimaryFP
        else:
            # self.logger.debug(
            #     "backupForwardingPaths:{0}".format(
            #         self.backupForwardingPaths))
            # self.logger.debug(
            #     "primaryForwardingPath:{0}\nfailureList:{1}\n"
            #     "key:{2}\npath:{3}".format(
            #         self.primaryForwardingPath, self.failureElementList, 
            #         key, backupForwardingPath))
            if not self.forwardingPathDict.has_key(rIndex):
                self.forwardingPathDict[rIndex] = [[]]
            else:
                self.logger.warning("Use notvia's path: {0}".format(
                        self.forwardingPathDict[rIndex]))

    def _mergePSFCBypassPath2ForwardingPath(self, key, inputByPassForwardingPath,
                                            inputBypassedPrimaryForwardingPath):
        byPassForwardingPath = copy.deepcopy(inputByPassForwardingPath)
        bypassedPrimaryForwardingPath = copy.deepcopy(inputBypassedPrimaryForwardingPath)

        if bypassedPrimaryForwardingPath == [[]]:
            return [[]]

        keyDict = self._parseBackupForwardingPathKey(key)
        failureNPoPID = keyDict['failureNPoPID']
        (vnfLayerNum, bp, Xp) = failureNPoPID
        self.logger.debug("failureNPoPID: {0}".format(failureNPoPID))

        startNPoPID = byPassForwardingPath[0][0][1]
        endNPoPID = byPassForwardingPath[-1][-1][1]

        stageNumOfPSFCPath = len(byPassForwardingPath)
        startNPoPServerID = bypassedPrimaryForwardingPath[vnfLayerNum][0]
        byPassForwardingPath[0].insert(0, startNPoPServerID)
        stopNPoPServerID = bypassedPrimaryForwardingPath[vnfLayerNum+stageNumOfPSFCPath-1][-1]
        byPassForwardingPath[-1].append(stopNPoPServerID)

        self.logger.debug("bypassedPrimaryForwardingPath:{0}".format(
            bypassedPrimaryForwardingPath))
        self.logger.debug("failureElementList:{0}".format(
            self.failureElementList))
        self.logger.debug("startNPoPID:{0}, endNPoPID:{1}".format(
            startNPoPID, endNPoPID))
        self.logger.debug("key:{0}".format(key))
        self.logger.debug("pSFC bypass Path:{0}".format(byPassForwardingPath))

        skipNum = 0
        if self.failureType == "link":
            # newForwardingPath = []
            # for segPathIndex, segPath in enumerate(bypassedPrimaryForwardingPath):
            #     newSegPath = None
            #     if skipNum>0:
            #         skipNum = skipNum - 1
            #         continue
            #     if len(segPath)>=4:
            #         (layerNum, lastSwitchID) = segPath[-3]
            #         (layerNum, lastSFFNodeID) = segPath[-2]
            #         (layerNum, nfviID) = segPath[-1]
            #         link1ID = (lastSwitchID, lastSFFNodeID)
            #         link2ID = (lastSFFNodeID, lastSwitchID)
            #         link3ID = (lastSFFNodeID, nfviID)
            #         link4ID = (nfviID, lastSFFNodeID)
            #         self.logger.debug("link1ID:{0},"
            #             "link2ID:{1},"
            #             "link3ID:{2},"
            #             "link4ID:{3},".format(link1ID,
            #                 link2ID, link3ID, link4ID))
            #         if (self._isLinkIDInFailureElementList(link1ID)
            #                 or self._isLinkIDInFailureElementList(link2ID)
            #                 or self._isLinkIDInFailureElementList(link3ID)
            #                 or self._isLinkIDInFailureElementList(link4ID)):
            #             newSegPath = copy.deepcopy(byPassForwardingPath)
            #             startServerID = segPath[0]
            #             newSegPath[0].insert(0, startServerID)
            #             skipNum = len(byPassForwardingPath)
            #             self.logger.debug(
            #                 "segPathIndex:{0}, skipNum:{1}".format(
            #                     segPathIndex, skipNum))
            #             endServerID = bypassedPrimaryForwardingPath[segPathIndex + skipNum - 1][-1]
            #             newSegPath[-1].append(endServerID)
            #             newForwardingPath.extend(newSegPath)
            #         else:
            #             newSegPath = segPath
            #             newForwardingPath.append(newSegPath)
            #     else:
            #         newSegPath = segPath
            #         newForwardingPath.append(newSegPath)

            # # self.logger.debug("newForwardingPath:{0}".format(
            # #         newForwardingPath))
            # # raw_input()

            # return newForwardingPath

            newForwardingPath = copy.deepcopy(bypassedPrimaryForwardingPath)
            link1ID = (newForwardingPath[vnfLayerNum][-1][1], newForwardingPath[vnfLayerNum][-2][1])
            link2ID = (newForwardingPath[vnfLayerNum][-2][1], newForwardingPath[vnfLayerNum][-1][1])
            link3ID = (newForwardingPath[vnfLayerNum][-3][1], newForwardingPath[vnfLayerNum][-2][1])
            link4ID = (newForwardingPath[vnfLayerNum][-2][1], newForwardingPath[vnfLayerNum][-3][1])
            if (self._isLinkIDInFailureElementList(link1ID)
                    or self._isLinkIDInFailureElementList(link2ID)
                    or self._isLinkIDInFailureElementList(link3ID)
                    or self._isLinkIDInFailureElementList(link4ID)):
                for stageCount in range(stageNumOfPSFCPath):
                    newForwardingPath[vnfLayerNum+stageCount] = byPassForwardingPath[stageCount]

            self.logger.debug("newForwardingPath:{0}".format(newForwardingPath))

            return newForwardingPath

        elif self.failureType == "node":
            raise ValueError(
                "Please implement failure type node")
        else:
            raise ValueError(
                "Unknown failure type:{0}".format(self.failureType))

    def _isForwardingPathAffectedByFailure(self, primaryForwardingPath):
        for element in self.failureElementList:
            if element == []:
                return False
            elif type(element) == Link:
                return self._isLinkInForwardingPath(element,
                        primaryForwardingPath)
            else:
                raise ValueError(
                    "Please implement failure type:{0}".format(
                        type(element)))

    def _isLinkInForwardingPath(self, link, forwardingPath):
        (srcID, dstID) = (link.srcID, link.dstID)
        for segPath in forwardingPath:
            for nodeIndex in range(len(segPath)-1):
                nodeID = segPath[nodeIndex][1]
                nextNodeID = segPath[nodeIndex+1][1]
                if ((nodeID == srcID and nextNodeID == dstID)
                        or (nodeID == dstID and nextNodeID == srcID)):
                    return True
        else:
            return False

    def _isE2EBackupForwardingPathUnderFailure(self, key, backupForwardingPath):
        for element in self.failureElementList:
            if type(element) == Link:
                if self._isLinkInForwardingPath(element, backupForwardingPath):
                    return False
                else:
                    return True

            else:
                raise ValueError(
                    "Please implement failure type:{0}".format(
                        type(element)))

    def _isBackupForwardingPathUnderFailure(self, key):
        for element in self.failureElementList:
            if type(element) == Link:
                keyDict = self._parseBackupForwardingPathKey(key)
                repairSwitchID = keyDict['repairSwitchID']
                if 'failureNodeID' in keyDict:
                    failureNodeID = keyDict['failureNodeID']
                    link = Link(repairSwitchID, failureNodeID)
                elif 'failureLinkID' in keyDict.keys():
                    failureLinkID = keyDict['failureLinkID']
                    link = Link(failureLinkID.srcID,
                        failureLinkID.dstID)
                else:
                    raise ValueError("Unsupport failure type")

                if self._isSameUndirectedLink(element, link):
                    return True
                else:
                    return False

            else:
                raise ValueError(
                    "Please implement failure type:{0}".format(
                        type(element)))

    def _parseBackupForwardingPathKey(self, key):
        keyDict = {}
        for item in key:
            keyName = item[0]
            value = item[1]
            keyDict[keyName] = value
        return keyDict

    def _isSameUndirectedLink(self, link1, link2):
        if ((link1.srcID == link2.srcID
                and link1.dstID == link2.dstID)
                or (link1.dstID == link2.srcID
                    and link1.srcID == link2.dstID)):
            return True
        else:
            return False

    def _isBypassPathUnderFailure(self, key):
        # self.logger.debug("key: {0}".format(key))
        for element in self.failureElementList:
            if type(element) == Link:
                keyDict = self._parseBackupForwardingPathKey(key)
                if self._isPSFCBypassPath(key):
                    (layerNum, failureNPoPID, Xp) = keyDict['failureNPoPID']
                    if self._isFailureNPoPPartOfFailureLink(layerNum,
                            failureNPoPID, element):
                        return True
                    else:
                        return False
                else:
                    raise ValueError("Impossible condition!")
                    # repairSwitchID = keyDict['repairSwitchID']
                    # failureNodeID = keyDict['failureNodeID']
                    # mergeSwitchID = keyDict['mergeSwitchID']

                    # link = Link(repairSwitchID, failureNodeID)
                    # if (element.srcID == repairSwitchID 
                    #         and element.dstID == failureNodeID):
                    #     return True
                    # else:
                    #     return False

            else:
                raise ValueError(
                    "Please implement failure type:{0}".format(
                        type(element)))

    def _isFailureNPoPPartOfFailureLink(self, layerNum, failureNPoPID, link):
        self.logger.debug("failureNPoPID: {0}".format(failureNPoPID))
        if not failureNPoPID in [link.srcID, link.dstID]:
            return False

        layerIndex = -1
        segPath = self.primaryForwardingPath[layerNum]

        self.logger.debug("segPath: {0}".format(segPath))
        self.logger.debug("link:{0}".format(link))

        layerIndex = layerIndex + 1
        for nodeIndex in range(len(segPath)-1):
            currentNodeID = segPath[nodeIndex][1]
            nextNodeIndex = nodeIndex + 1
            nextNodeID = segPath[nextNodeIndex][1]
            if ((link.srcID == currentNodeID 
                    and link.dstID == nextNodeID)
                        or (link.srcID == nextNodeID
                            and link.dstID == currentNodeID)):
                return True
        else:
            return False
