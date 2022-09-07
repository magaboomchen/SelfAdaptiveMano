#!/usr/bin/python
# -*- coding: UTF-8 -*-

import copy
import random
from typing import Union

import networkx as nx

from sam.base.link import Link
from sam.base.sfc import SFC, SFCI
from sam.base.switch import Switch
from sam.base.server import Server
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.vnf import PREFERRED_DEVICE_TYPE_P4, PREFERRED_DEVICE_TYPE_SERVER
from sam.measurement.dcnInfoBaseMaintainer import DCNInfoBaseMaintainer
from sam.orchestration.algorithms.base.performanceModel import PerformanceModel

WEIGHT_TYPE_CONST = "WEIGHT_TYPE_CONST"
WEIGHT_TYPE_PROPAGATION_DELAY_MODEL = "WEIGHT_TYPE_PROPAGATION_DELAY_MODEL"
WEIGHT_TYPE_DELAY_MODEL = "WEIGHT_TYPE_DELAY_MODEL"
WEIGHT_TYPE_01_UNIFORAM_MODEL = "WEIGHT_TYPE_01_UNIFORAM_MODEL"
WEIGHT_TYPE_0100_UNIFORAM_MODEL = "WEIGHT_TYPE_0100_UNIFORAM_MODEL"


class MultiLayerGraph(object):
    def __init__(self, enablePreferredDeviceSelection=False):
        logConfigur = LoggerConfigurator(__name__, './log',
            'MultiLayerGraph.log', level='debug')
        self.logger = logConfigur.getLogger()
        self.enablePreferredDeviceSelection = enablePreferredDeviceSelection
        self.pM = PerformanceModel()

    def loadInstance4dibAndRequest(self, dib,   # type: DCNInfoBaseMaintainer
                                    request,
                                    weightType,
                                    connectingLinkWeightType=WEIGHT_TYPE_CONST
                                ):
        self._dib = dib 
        self.request = request
        self.sfc = request.attributes['sfc']    # type: SFC
        self.sfcLength = self.sfc.getSFCLength()    # type: int
        self.zoneName = self.sfc.attributes['zone'] # type: str
        self.sfci = request.attributes['sfci']  # type: SFCI
        self.weightType = weightType
        self.connectingLinkWeightType = connectingLinkWeightType
        self.abandonNodeIDList = []
        self.abandonLinkIDList = []

    def addAbandonNodeIDs(self, nodeIDList):
        for nodeID in nodeIDList:
            self.abandonNodeIDList = self.abandonNodeIDList.append(nodeID)

    def addAbandonNodes(self, nodeList):
        # type: (list(Union[Switch, Server])) -> None
        for node in nodeList:
            if type(node) == Server:
                nodeID = node.getServerID()
            elif type(node) == Switch:
                nodeID = node.switchID
            else:
                raise ValueError("Invalid node type:{0}".format(type(node)))
            self.abandonNodeIDList.append(nodeID)

    def addAbandonLinkIDs(self, linkIDList):
        for linkID in linkIDList:
            self.abandonLinkIDList = self.abandonLinkIDList.append(linkID)

    def addAbandonLinks(self, linkList):
        for link in linkList:
            if type(link) == Link:
                linkID = (link.srcID, link.dstID)
            else:
                raise ValueError("Invalid link type:{0}".format(type(link)))
            self.abandonLinkIDList.append(linkID)

    def trans2MLG(self, capacityAwareFlag=True):
        gList = []
        for stage in range(self.sfcLength+1):
            g = self.genOneLayer(stage, capacityAwareFlag)
            gList.append(g)

        mLG = nx.compose_all(gList)
        self._connectLayersInMLG(mLG)
        self.multiLayerGraph = mLG

    def genOneLayer(self, stage, capacityAwareFlag=True):
        graph = nx.DiGraph()
        edgeList = []

        expectedBandwidth = self._getExpectedBandwidth(stage)
        expectedTCAM = self._getExpectedTCAM(stage)

        linksInfoDict = self._dib.getLinksByZone(self.zoneName, pruneInactiveLinks=True)
        for key, linkInfoDict in linksInfoDict.items():
            link = linkInfoDict['link'] # type: Link
            srcNodeID = link.srcID
            dstNodeID = link.dstID
            if (self._dib.isServerID(srcNodeID) 
                    or self._dib.isServerID(dstNodeID)):
                continue
            if not (self._dib.isSwitchActive(srcNodeID, self.zoneName) 
                        and self._dib.isSwitchActive(dstNodeID, self.zoneName)):
                self.logger.warning(" link {0}-{1} inactive ".format(srcNodeID, dstNodeID))
                continue
            srcLayerNodeID = self._genLayerNodeID(srcNodeID, stage)
            dstLayerNodeID = self._genLayerNodeID(dstNodeID, stage)
            weight = self.getLinkWeight(link)
            # self.logger.debug(
            #     "resource link:{0}, node1:{1}, node2:{2}".format(
            #         self._dib.hasEnoughLinkResource(link, expectedBandwidth),
            #         self._dib.hasEnoughSwitchResource(srcNodeID, expectedTCAM),
            #         self._dib.hasEnoughSwitchResource(dstNodeID, expectedTCAM)
            #     ))
            if ((self._dib.hasEnoughLinkResource(link, expectedBandwidth,
                    self.zoneName) 
                and self._dib.hasEnoughSwitchResource(srcNodeID,
                    expectedTCAM, self.zoneName)
                and self._dib.hasEnoughSwitchResource(dstNodeID,
                    expectedTCAM, self.zoneName)
                ) or (  not capacityAwareFlag  )):
                if not self._isAbandonLink(link):
                    edgeList.append((srcLayerNodeID, dstLayerNodeID, weight))
                    self.logger.info(" add edge {0}-{1} to edgeList. ".format(srcLayerNodeID, dstLayerNodeID))
            else:
                self.logger.warning(
                    "Link {0}->{1} hasn't enough resource.".format(
                        srcNodeID, dstNodeID
                    ))
        graph.add_weighted_edges_from(edgeList)

        # self.logger.debug("A layer graph nodes:{0}".format(graph.nodes))
        # self.logger.debug("A layer graph edges:{0}".format(graph.edges))
        # self.logger.debug("edges number:{0}".format(len(graph.edges)))

        connectionFlag = nx.is_weakly_connected(copy.deepcopy(graph))
        if connectionFlag == False:
            self.logger.debug("is_connected:{0}".format(connectionFlag))
            # nx.draw(graph, with_labels=True)
            # plt.savefig("./temp.png")
            # plt.show()

        return graph

    def _getExpectedBandwidth(self, stageNum):
        if self.sfc.isFixedResourceQuota():
            if stageNum > len(self.sfc.vNFTypeSequence)-1:
                vnfType = self.sfc.vNFTypeSequence[-1]
            else:
                vnfType = self.sfc.vNFTypeSequence[stageNum]
            cpuQuota = self.sfc.vnfiResourceQuota['cpu']
            maxThroughput = self.pM.getVNFIExpectedThroughput(vnfType, cpuQuota)
            trafficDemand = self.sfc.getSFCTrafficDemand()
            expectedBandwidth = min(maxThroughput, trafficDemand)
        else:
            trafficDemand = self.sfc.getSFCTrafficDemand()
            expectedBandwidth = trafficDemand
        return (stageNum+1) * expectedBandwidth

    def _getExpectedTCAM(self, stage):
        return stage+1

    def _genLayerNodeID(self, nodeID, stage):
        return (stage, nodeID)

    def getLinkWeight(self, link, isConnectingLink=False):
        if isConnectingLink:
            weightType = self.connectingLinkWeightType
        else:
            weightType = self.weightType

        if weightType == WEIGHT_TYPE_CONST:
            return 1
        elif weightType == WEIGHT_TYPE_PROPAGATION_DELAY_MODEL:
            return self._getLinkPropagationLatency(link)
        elif weightType == WEIGHT_TYPE_DELAY_MODEL:
            linkUtil = self._getLinkUtil(link)
            return self._getLinkLatency(link, linkUtil)
        elif weightType == WEIGHT_TYPE_01_UNIFORAM_MODEL:
            return random.random()
        elif weightType == WEIGHT_TYPE_0100_UNIFORAM_MODEL:
            return random.random() * 100
        else:
            raise ValueError("Unknown weight type.")

    def _isAbandonLink(self, link):
        srcID = link.srcID
        dstID = link.dstID
        if ( (srcID, dstID) in self.abandonLinkIDList
            or srcID in self.abandonNodeIDList
            or dstID in self.abandonNodeIDList):
            return True
        else:
            return False

    def _getLinkUtil(self, link):
        reservedBandwidth = self._dib.getLinkReservedResource(
            link.srcID, link.dstID, self.zoneName)
        bandwidth = link.bandwidth
        return reservedBandwidth*1.0/bandwidth

    def _getLinkPropagationLatency(self, link):
        return self.pM.getPropogationLatency(link.linkLength)

    def _getLinkLatency(self, link, linkUtil):
        return self.pM.getLatencyOfLink(link, linkUtil)

    def _connectLayersInMLG(self, mLG):
        for stage in range(self.sfcLength):
            self._connectLayer(mLG, stage, stage+1)

    def _connectLayer(self, mLG, layer1Num, layer2Num):
        # type: (MultiLayerGraph, int, int) -> None
        switches = self._getSupportNFAndVNFSwitchesOfLayer(layer1Num)
        # self.logger.debug("switches:{0}".format(switches))
        # self.logger.debug("connect layer")
        for switch in switches:
            nodeID = switch.switchID
            srcLayerNodeID = self._genLayerNodeID(nodeID, layer1Num)
            dstLayerNodeID = self._genLayerNodeID(nodeID, layer2Num)
            link = Link(srcLayerNodeID, dstLayerNodeID)
            pDT = self._getPreferredDeviceTypeOfIdxVNF(self.sfc, layer1Num)
            if (self.enablePreferredDeviceSelection
                    and pDT == PREFERRED_DEVICE_TYPE_P4):
                vnf = self.sfc.vnfSequence[layer1Num]
                if self._dib.hasEnoughP4SwitchResources(
                            nodeID, vnf, self.zoneName):
                    weight = self.getLinkWeight(link, isConnectingLink=True)
                    mLG.add_edge(srcLayerNodeID, dstLayerNodeID, weight=weight)
                else:
                    self.logger.warning(
                        "P4 switch {0} hasn't enough server resource.".format(
                            nodeID
                        ))
            elif ((not self.enablePreferredDeviceSelection)
                    or pDT == PREFERRED_DEVICE_TYPE_SERVER):
                (expectedCores, expectedMemory, expectedBandwidth) \
                    = self._getExpectedServerResource(layer1Num)
                # self.logger.debug(
                #     "expected Cores:{0}, Memory:{1}, bandwdith:{2}".format(
                #         expectedCores, expectedMemory, expectedBandwidth
                # ))
                if self._dib.hasEnoughNPoPServersResources(
                        nodeID, expectedCores, expectedMemory, expectedBandwidth,
                            self.zoneName, self.abandonNodeIDList):
                    weight = self.getLinkWeight(link, isConnectingLink=True)
                    # self.logger.debug("weight:{0}".format(weight))
                    mLG.add_edge(srcLayerNodeID, dstLayerNodeID, weight=weight)
                else:
                    self.logger.warning(
                        "NPoP {0} hasn't enough server resource.".format(
                            nodeID
                        ))
            else:
                raise ValueError("Unknown preferred device")

    def _getSupportNFAndVNFSwitchesOfLayer(self, layerNum):
        # type: (int) -> list(Switch)
        switches = []
        vnfType = self.sfc.vNFTypeSequence[layerNum]
        for switchInfoDict in self._dib.getSwitchesByZone(self.zoneName, 
                                    pruneInactiveSwitches=True).values():
            switch = switchInfoDict['switch']
            if self.enablePreferredDeviceSelection:
                pDT = self._getPreferredDeviceTypeOfIdxVNF(self.sfc, layerNum)
                if pDT == PREFERRED_DEVICE_TYPE_P4:
                    if vnfType in switch.supportNF:
                        switches.append(switch)
                elif pDT == PREFERRED_DEVICE_TYPE_SERVER:
                    if vnfType in switch.supportVNF:
                        switches.append(switch)
                else:
                    pass
            else:
                if vnfType in switch.supportVNF:
                    switches.append(switch)
        return switches

    def _getPreferredDeviceTypeOfIdxVNF(self, sfc, idx):
        # type: (SFC, int) -> str
        pDT = sfc.vnfSequence[idx].preferredDeviceType
        return pDT

    def _getExpectedServerResource(self, layerNum):
        if self.sfc.isFixedResourceQuota():
            cpuQuota = self.sfc.vnfiResourceQuota['cpu']
            memQuota = self.sfc.vnfiResourceQuota['mem']
            expectedBandwidth = self._getExpectedBandwidth(layerNum)
            return (cpuQuota, memQuota, expectedBandwidth)
        else:
            vnfType = self.sfc.vNFTypeSequence[layerNum]
            trafficDemand = self.sfc.getSFCTrafficDemand()
            return self.pM.getExpectedServerResource(vnfType, trafficDemand)

    def getPath(self, startLayer, startNodeID, endLayer, endNodeID):
        startNodeInMLG = (startLayer, startNodeID)
        endNodeInMLG = (endLayer, endNodeID)

        try:
            path = nx.dijkstra_path(self.multiLayerGraph,
                startNodeInMLG, endNodeInMLG)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex)
            connectionFlag = nx.is_weakly_connected(copy.deepcopy(
                self.multiLayerGraph))
            self.logger.error("multi-layer-graph is_connected:{0}".format(
                connectionFlag))
            # nx.draw(self.multiLayerGraph, with_labels=True)
            # plt.savefig("./disconnection.png")
            # plt.show()
            self.logger.error(
                    "can't compute path for {0} -> {1}".format(
                    (startLayer, startNodeID), (endLayer, endNodeID)
                )
            )
            raise ValueError("can't compute path for {0} -> {1}".format(
                (startLayer, startNodeID), (endLayer, endNodeID)
            ))

        # self.logger.debug("get path from {0}->{1}:{2}".format(
        #     startNodeInMLG, endNodeInMLG, path))

        return path

    def catPath(self, firstHalfPath, secondHalfPath):
        lastNode = firstHalfPath[-1]
        firstNode = secondHalfPath[0]
        if lastNode == firstNode:
            concatenatedPath = firstHalfPath + secondHalfPath[1:]
        else:
            concatenatedPath = firstHalfPath + secondHalfPath
        return concatenatedPath

    def deLoop(self, path):
        pathTmp = copy.deepcopy(path)
        # self.logger.debug("path:{0}".format(path))
        while self.hasLoop(pathTmp):
            deDuplicateFlag = False
            for index in range(len(pathTmp)):
                node = pathTmp[index]
                searchList = range(index+1, len(pathTmp))
                searchList.reverse()
                for indexPoint in searchList:
                    nodePoint = pathTmp[indexPoint]
                    if nodePoint == node:
                        deDuplicateFlag = True
                        newPathTmp = pathTmp[0:index] + pathTmp[indexPoint:]
                        # self.logger.debug("newPathTmp:{0}".format(newPathTmp))
                        break
                if deDuplicateFlag == True:
                    pathTmp = copy.deepcopy(newPathTmp)
                    break
        return pathTmp

    def hasLoop(self, path):
        for node in path:
            if path.count(node) > 1:
                return True
        else:
            return False

    def getVnfLayerNum(self, vnfType, sfc):
        c = sfc.getSFCLength()
        if vnfType == 0:
            return 0
        elif vnfType == -1:
            return c+1
        for index in range(c):
            if vnfType == sfc.vNFTypeSequence[index]:
                return index
        else:
            raise ValueError("getVnfLayerNum: can't find vnf")

    def getVnfLayerNumOfBackupVNF(self, vnfIType, vnfJType, sfc):
        c = sfc.getSFCLength()
        if vnfIType == 0:
            vnfType = vnfJType
        elif vnfJType == -1:
            vnfType = vnfIType
        else:
            # raise ValueError("vnfType != vnfIType:{0} or vnfJtype{1}".format(
            #         vnfIType, vnfJType))
            vnfType = vnfIType

        for index in range(c):
            if vnfType == sfc.vNFTypeSequence[index]:
                return index
        else:
            raise ValueError("getVnfLayerNumOfBackupVNF: can't find vnf")

    def getStartAndEndlayerNum(self, Xp, sfc):
        firstVNFType = Xp[0]
        endVNFType = Xp[-1]

        c = sfc.getSFCLength()
        for index in range(c):
            if firstVNFType == sfc.vNFTypeSequence[index]:
                startLayerNum = index
            if endVNFType == sfc.vNFTypeSequence[index]:
                endLayerNum = index + 1

        if (startLayerNum == None or endLayerNum == None):
            raise ValueError("getVnfLayerNumOfBackupVNF: can't find vnf")

        return (startLayerNum, endLayerNum)
