#!/usr/bin/python
# -*- coding: UTF-8 -*-

import copy

from sam.base.server import Server
from sam.base.switch import Switch
from sam.base.link import Link
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.orchestration.algorithms.base.multiLayerGraph import MultiLayerGraph, \
    WEIGHT_TYPE_DELAY_MODEL
from sam.orchestration.algorithms.base.frrPathIDAllocator import FRRPathIDAllocator
from sam.orchestration.algorithms.base.failureScenario import FailureScenario
from sam.orchestration.algorithms.base.resourceAllocator import ResourceAllocator
from sam.orchestration.algorithms.mMLPSFC.mMLPSFC import MMLPSFC


class MMLBSFC(MMLPSFC):
    def __init__(self, dib, requestList, forwardingPathSetsDict):
        self._initDib = dib
        self._dib = dib
        self.requestList = requestList
        self.forwardingPathSetsDict = forwardingPathSetsDict

        logConfigur = LoggerConfigurator(__name__,
            './log', 'MMLBSFC.log', level='debug')
        self.logger = logConfigur.getLogger()

        self.failureType = "node"
        self.zoneName = self.requestList[0].attributes['zone']
        self._genRequestIngAndEg()
        self._genAllFailureScenarios()

        self._fpIDA = FRRPathIDAllocator(self.requestList)

    def mapSFCI(self):
        self.logger.info("MMLBSFC mapSFCI")
        self._mapBackupPath4AllFailureScenarios()
        return self.forwardingPathSetsDict

    def _genAllFailureScenarios(self):
        if self.failureType == "node":
            # node protection: switch and server
            self.scenarioList = []
            switchesInfoDict = self._initDib.getSwitchesByZone(self.zoneName)
            for switchInfoDict in switchesInfoDict.itervalues():
                switch = switchInfoDict['switch']
                fS = FailureScenario()
                fS.addElement(switch)
                self.scenarioList.append(fS)

            serversInfoDict = self._initDib.getServersByZone(self.zoneName)
            for serverInfoDict in serversInfoDict.itervalues():
                server = serverInfoDict['server']
                fS = FailureScenario()
                fS.addElement(server)
                self.scenarioList.append(fS)

        elif self.failureType == "link":
            # link protection: link
            self.scenarioList = []
            linksInfoDict = self._initDib.getLinksByZone(self.zoneName)
            for linkInfoDict in linksInfoDict.itervalues():
                link = linkInfoDict['link']
                fS = FailureScenario()
                fS.addElement(link)
                self.scenarioList.append(fS)

        else:
            raise ValueError("unknown faiulre type: {0}".format(self.failureType))

    def _mapBackupPath4AllFailureScenarios(self):
        for scenario in self.scenarioList:
            self._mapBackupPath4Scenario(scenario)

    def _mapBackupPath4Scenario(self, scenario):
        self._init(scenario)
        self._allocateResource4UnaffectedPart()
        self._genBackupPath4EachRequest()

    def _init(self, scenario):
        self._dib = copy.deepcopy(self._initDib)
        self.failureElementList = scenario.getElementsList()
        self.failureScenario = scenario
        self.backupPathDict = {}
        self.unaffectedForwardingPathSegDict = {}
        # {rIndex: unaffected part of forwardingPath}

    def _allocateResource4UnaffectedPart(self):
        for rIndex in range(len(self.requestList)):
            if not self._isRequestAffectedByFailure(rIndex):
                fp = self._getPrimaryForwardingPath(rIndex)
                self.addForwardingPath2UnaffectedForwardingPathSegDict(
                    rIndex, fp)
            else:
                # self.logger.debug(
                #     "rIndex:{0} is affected by failureScenario:{1}".format(
                #         rIndex, self.failureElementList))
                fp = self._getPrimaryForwardingPath(rIndex)
                segFp = self._getUnaffectedPartOfPrimaryForwardingPath(
                    rIndex, fp)
                self.logger.debug("segFp:{0}".format(segFp))
                self.addForwardingPath2UnaffectedForwardingPathSegDict(
                    rIndex, segFp)

        rA = ResourceAllocator(self._dib, self.zoneName)
        rA.allocate4UnaffectedForwardingPathSegDict(
            self.requestList, self.unaffectedForwardingPathSegDict)

    def _getPrimaryForwardingPath(self, rIndex):
        return self.forwardingPathSetsDict[rIndex].primaryForwardingPath[1]

    def _isRequestAffectedByFailure(self, rIndex):
        primaryForwardingPath = self._getPrimaryForwardingPath(rIndex)

        if self.failureType == "node":
            for segPath in primaryForwardingPath:
                for layerNum, nodeID in segPath:
                    if self._isNodeIDInFailureElementList(nodeID):
                        return True
            return False

        elif self.failureType == "link":
            for segPath in primaryForwardingPath:
                for nodeIndex in range(len(segPath)-1):
                    (srcLayerNum, srcNodeID) = segPath[nodeIndex]
                    (dstLayerNum, dstNodeID) = segPath[nodeIndex+1]
                    linkID = (srcNodeID, dstNodeID)
                    if self._isLinkIDInFailureElementList(linkID):
                        return True
            return False

        else:
            raise ValueError("unknown faiulre type: {0}".format(self.failureType))

    def _getUnaffectedPartOfPrimaryForwardingPath(self, 
                rIndex, primaryForwardingPath):
        unaffectedPart = []
        if self.failureType == "node":
            for segPath in primaryForwardingPath:
                partOfSegPath = []
                for layerNum, nodeID in segPath:
                    if self._isNodeIDInFailureElementList(nodeID):
                        unaffectedPart.append(partOfSegPath)
                        return unaffectedPart
                    else:
                        partOfSegPath.append((layerNum, nodeID))
                unaffectedPart.append(segPath)
            return unaffectedPart

        elif self.failureType == "link":
            for segPath in primaryForwardingPath:
                partOfSegPath = []
                for nodeIndex in range(len(segPath)-1):
                    (srcLayerNum, srcID) = segPath[nodeIndex]
                    (dstLayerNum, dstID) = segPath[nodeIndex+1]
                    linkID1 = (srcID, dstID)
                    linkID2 = (dstID, srcID)
                    partOfSegPath.append((srcLayerNum, srcID))
                    if (self._isLinkIDInFailureElementList(linkID1)
                            or self._isLinkIDInFailureElementList(linkID2)):
                        unaffectedPart.append(partOfSegPath)
                        return unaffectedPart
                    else:
                        pass
                    if nodeIndex == len(segPath)-1:
                        partOfSegPath.append((dstLayerNum, dstID))
                unaffectedPart.append(segPath)
            return unaffectedPart

        else:
            raise ValueError("Unknown failure type:{0}".format(self.failureType))

    def addForwardingPath2UnaffectedForwardingPathSegDict(self,
            rIndex, segFp):
        self.unaffectedForwardingPathSegDict[rIndex] = segFp

    def _isNodeIDInFailureElementList(self, nodeID):
        for element in self.failureElementList:
            if type(element) == Switch:
                elementID = element.switchID
            elif type(element) == Server:
                elementID = element.getServerID()
            else:
                pass

            if elementID == nodeID:
                return True
        else:
            return False

    def _isLinkIDInFailureElementList(self, linkID):
        for element in self.failureElementList:
            if type(element) == Link:
                elementID = (element.srcID, element.dstID)
            else:
                pass

            if elementID == linkID:
                return True
        else:
            return False

    def _genBackupPath4EachRequest(self):
        for rIndex in range(len(self.requestList)):
            if not self._isRequestAffectedByFailure(rIndex):
                continue

            self.request = self.requestList[rIndex]
            sfc = self.request.attributes['sfc']
            c = sfc.getSFCLength()

            fp = self._getPrimaryForwardingPath(rIndex)
            try:
                if not self._hasRepairSwitch(fp, self.failureElementList):
                    continue
                (layerNum, repairSwitchID) = self._getRepairSwitchLayerSwitchID(
                    fp, self.failureElementList)
            except Exception as ex:
                ExceptionProcessor(self.logger).logException(ex)
                continue
            egSwitchID = self.requestEgSwitchID[rIndex]

            capacityAwareFlag = True
            while True:
                try:
                    mlg = MultiLayerGraph()
                    mlg.loadInstance4dibAndRequest(self._dib, 
                        self.request, WEIGHT_TYPE_DELAY_MODEL)
                    if self.failureType == "node":
                        mlg.addAbandonNodes(self.failureElementList)
                    elif self.failureType == "link":
                        mlg.addAbandonLinks(self.failureElementList)
                    else:
                        pass
                    mlg.trans2MLG(capacityAwareFlag)
                    path = mlg.getPath(layerNum, repairSwitchID, c, egSwitchID)
                    path = self._selectNPoPNodeAndServers(path, rIndex)
                    self.logger.debug("path:{0}".format(path))
                    break
                except Exception as ex:
                    ExceptionProcessor(self.logger).logException(ex)
                    self.logger.warning(
                        "Can't find valid backup path for request {0}"
                        " under resource capacity constraints".format(
                            rIndex))
                    self.logger.warning("primary forwarding path: {0}".format(fp))
                    self.logger.warning("failureElementList:{0}".format(
                        self.failureElementList))
                    self.logger.warning("repairSwitchID: {0}".format(
                        repairSwitchID))
                    if capacityAwareFlag == True:
                        capacityAwareFlag = False
                    else:
                        raise ValueError(
                            "Can't find valid backup path for"
                            "request {0} even without resource capacity"
                            "constraint".format(rIndex))

            uFPSDict = copy.deepcopy(self.unaffectedForwardingPathSegDict)
            forwardingPathSetDict = self._genForwardingPathSet4Scenario(
                uFPSDict, rIndex, path)

            if self._isPathsMeetLatencySLA(self._dib, forwardingPathSetDict,
                                            self.requestList):
                self.backupPathDict[rIndex] = path
                self._allocateResource(path)
            else:
                raise ValueError(
                    "Can't find valid primary path for request {0}".format(
                        rIndex))

            fpSet = self.forwardingPathSetsDict[rIndex]
            bfpDict = fpSet.backupForwardingPath[1]
            failureElementID = self.failureScenario.getFailureElementsIDInList()[0]
            newPathID = self._fpIDA.genPathID(rIndex, failureElementID)
            if self.failureType == "node":
                bfpDict[(
                        ("failureNodeID", failureElementID),
                        ("repairMethod", "fast-reroute"),
                        ("repairSwitchID", repairSwitchID),
                        ("newPathID", newPathID)
                    )] = path
            elif self.failureType == "link":
                bfpDict[(
                        ("failureLinkID", failureElementID),
                        ("repairMethod", "fast-reroute"),
                        ("repairSwitchID", repairSwitchID),
                        ("newPathID", newPathID)
                    )] = path
            else:
                pass

    def _hasRepairSwitch(self, forwardingPath, failureElementList):
        self.failureElementList = failureElementList
        if self.failureType == "node":
            impossibleNodeList = []
            impossibleNodeList.extend([
                forwardingPath[0][0][1],    # source server can't be repaired
                forwardingPath[0][1][1],    # first sff can't be repaired
                forwardingPath[-1][-1][1],  # destination server can't be repaired
                forwardingPath[-1][-2][1]   # last sff can't be repaired
                ]
            )
            for nodeID in impossibleNodeList:
                if self._isNodeIDInFailureElementList(nodeID):
                    return False

            for segPath in forwardingPath:
                # the first node can't be repaired, e.g. source server or nfvi
                (layerNum, nodeID) = segPath[0]
                if self._isNodeIDInFailureElementList(nodeID):
                    return False

                # the following node in segPath can be repair by latter switch
                for layerNodeIndex in range(len(segPath)-1):
                    (layerNum, nodeID) = segPath[layerNodeIndex]
                    (nextLayerNum, nextNodeID) = segPath[layerNodeIndex+1]
                    if (self._isNodeIDInFailureElementList(nextNodeID) 
                            and self._dib.isSwitchID(nodeID)):
                        return True
            else:
                return False

        elif self.failureType == "link":
            impossibleLinkList = []
            impossibleLinkList.extend([
                # source server -> first sff can't be repaired
                (forwardingPath[0][0][1], forwardingPath[0][1][1]),
                (forwardingPath[0][1][1], forwardingPath[0][0][1]),
                # last sff -> destination server can't be repaired
                (forwardingPath[-1][-1][1], forwardingPath[-1][-2][1]),
                (forwardingPath[-1][-2][1], forwardingPath[-1][-1][1])
                ]
            )
            for linkID in impossibleLinkList:
                if self._isLinkIDInFailureElementList(linkID):
                    return False

            return True

        else:
            raise ValueError("Unknown failure type:{0}".format(self.failureType))

    def _getRepairSwitchLayerSwitchID(self, forwardingPath,
            failureElementList):
        self.failureElementList = failureElementList
        if self.failureType == "node":
            for segPath in forwardingPath:
                for layerNodeIndex in range(len(segPath)-1):
                    (layerNum, nodeID) = segPath[layerNodeIndex]
                    (nextLayerNum, nextNodeID) = segPath[layerNodeIndex+1]
                    if self._isNodeIDInFailureElementList(nextNodeID):
                        return (layerNum, nodeID)
            else:
                raise ValueError(
                    "Can't find repair switch in failure"\
                        " scenario {0} for forwarding path {1}".format(
                        self.failureScenario.getFailureElementsIDInList(),
                        forwardingPath))

        elif self.failureType == "link":
            for segPath in forwardingPath:
                for layerNodeIndex in range(len(segPath)-1):
                    (layerNum, nodeID) = segPath[layerNodeIndex]
                    (nextLayerNum, nextNodeID) = segPath[layerNodeIndex+1]
                    linkID1 = (nodeID, nextNodeID)
                    linkID2 = (nextNodeID, nodeID)
                    if (self._isLinkIDInFailureElementList(linkID1)
                            or self._isLinkIDInFailureElementList(linkID2)):
                        return (layerNum, nodeID)
            else:
                raise ValueError(
                    "Can't find repair switch in failure"\
                        " scenario {0} for forwarding path {1}".format(
                        self.failureScenario.getFailureElementsIDInList(),
                        forwardingPath))

        else:
            raise ValueError(
                "Unknown failure type:{0}".format(self.failureType))

    def _selectNPoPNodeAndServers(self, path, rIndex):
        self.logger.debug("path: {0}".format(path))
        # Example 1
        # before adding servers
        # [(3, 8), (3, 1), (3, 10), (3, 19)]
        # after adding servers
        # [
        #   [(3, 8), (3, 1), (3, 10), (3, 19), (0, 10024)]
        # ]

        request = self.requestList[rIndex]

        dividedPath = self._dividePath(path)
        self.logger.debug("dividedPath: {0}".format(dividedPath))

        # add ingress and egress
        egID = self._getEgressID(request)
        dividedPath = self._addEndNodeID2DividedPath(dividedPath, egID)
        self.logger.debug("after add endNode's dividedPath: {0}".format(
            dividedPath))

        # select a server for each stage
        serverList = self._selectNFVI4EachStage(dividedPath, request,
                self.failureScenario.getFailureElementsIDInList())
        dividedPath = self._addNFVI2Path(dividedPath, serverList)
        self.logger.info("egID:{0}, dividedPath:{1}".format(
                egID, dividedPath))

        return dividedPath

    def _genForwardingPathSet4Scenario(self, uFPSDict, thisRIndex, path):
        # In MML-BSFC,
        # uFPSDict == self.unaffectedForwardingPathSegDict 
        # path == self.backupPathDict[rIndex]

        # merge existed request' backup path into unaffectedForwardingPathSeg
        for rIndex in self.backupPathDict.keys():
            firstHalfPath = uFPSDict[rIndex]
            backupPath = self.backupPathDict[rIndex]
            # self.logger.debug("firstHalfPath:{0}, backupPath:{1}".format(
            #     firstHalfPath, backupPath
            # ))
            # raw_input()  # type: ignore
            if self._isRequestAffectedByFailure(rIndex):
                uFPSDict[rIndex] = self._mergePath2UFP(backupPath,
                    uFPSDict[rIndex])

        # merge thisRequest's backup path into unaffectedForwardingPathSeg
        if self._isRequestAffectedByFailure(thisRIndex):
            uFPSDict[thisRIndex] = self._mergePath2UFP(path,
                uFPSDict[thisRIndex])

        return uFPSDict

    def _mergePath2UFP(self, path, unaffectedForwardingPath):
        uFP = copy.deepcopy(unaffectedForwardingPath)
        (repairNodeLayerNum, repairNodeID) = path[0][0]
        # self.logger.debug("repairNodeLayerNum:{0}, repairNodeID:{1}".format(
        #     repairNodeLayerNum, repairNodeID))
        # self.logger.debug("attached path:{0}".format(path))
        # self.logger.debug("before merged uFP:{0}".format(uFP))

        # concatenate repair node with path
        uFP[-1].extend(path[0][1:])
        # uFP[-1].extend(path[0][:])

        # append following backup path
        uFP.extend(path[1:])

        # self.logger.debug("merged uFP:{0}".format(uFP))

        return uFP
