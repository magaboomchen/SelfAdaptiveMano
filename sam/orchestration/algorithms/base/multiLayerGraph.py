#!/usr/bin/python
# -*- coding: UTF-8 -*-

import copy
import math
import random

import networkx as nx
import gurobipy as gp
from gurobipy import *
from gurobipy import GRB
# import matplotlib
# matplotlib.use('Agg')
# import matplotlib.pyplot as plt

from sam.base.path import *
from sam.base.link import Link, LINK_DEFAULT_BANDWIDTH
from sam.base.switch import *
from sam.base.server import *
from sam.base.messageAgent import *
from sam.base.socketConverter import SocketConverter, BCAST_MAC
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.orchestration.algorithms.base.performanceModel import *

WEIGHT_TYPE_CONST = "WEIGHT_TYPE_CONST"
WEIGHT_TYPE_PROPAGATION_DELAY_MODEL = "WEIGHT_TYPE_PROPAGATION_DELAY_MODEL"
WEIGHT_TYPE_DELAY_MODEL = "WEIGHT_TYPE_DELAY_MODEL"
WEIGHT_TYPE_01_UNIFORAM_MODEL = "WEIGHT_TYPE_01_UNIFORAM_MODEL"
WEIGHT_TYPE_0100_UNIFORAM_MODEL = "WEIGHT_TYPE_0100_UNIFORAM_MODEL"


class MultiLayerGraph(object):
    def __init__(self):
        logConfigur = LoggerConfigurator(__name__, './log',
            'MultiLayerGraph.log', level='debug')
        self.logger = logConfigur.getLogger()

    def loadInstance4dibAndRequest(self, dib, request, weightType,
                                    connectingLinkWeightType=WEIGHT_TYPE_CONST):
        self._dib = dib
        self.request = request
        self.sfc = request.attributes['sfc']
        self.sfcLength = self.sfc.getSFCLength()
        self.zoneName = self.sfc.attributes['zone']
        self.weightType = weightType
        self.connectingLinkWeightType = connectingLinkWeightType
        self.abandonNodeIDList = []
        self.abandonLinkIDList = []

    def addAbandonNodeIDs(self, nodeIDList):
        for nodeID in nodeIDList:
            self.abandonNodeIDList = self.abandonNodeIDList + nodeIDList

    def addAbandonNodes(self, nodeList):
        for node in nodeList:
            if type(node) == Server:
                nodeID = node.getServerID()
            elif type(node) == Switch:
                nodeID = node.switchID
            else:
                raise ValueError("Invalid node type:{0}".format(type(node)))
            self.abandonNodeIDList.append(nodeID)

    def addAbandonLinkIDs(self, linkIDList):
        for link in linkIDList:
            self.abandonLinkIDList = self.abandonLinkIDList + linkIDList

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
        G = nx.DiGraph()
        edgeList = []

        expectedBandwidth = self._getExpectedBandwidth(stage)
        expectedTCAM = self._getExpectedTCAM(stage)

        linksInfoDict = self._dib.getLinksByZone(self.zoneName)
        for linkInfoDict in linksInfoDict.itervalues():
            link = linkInfoDict['link']
            srcLayerNodeID = self._genLayerNodeID(link.srcID, stage)
            dstLayerNodeID = self._genLayerNodeID(link.dstID, stage)
            weight = self.getLinkWeight(link)
            # self.logger.debug(
            #     "resource link:{0}, node1:{1}, node2:{2}".format(
            #         self._dib.hasEnoughLinkResource(link, expectedBandwidth),
            #         self._dib.hasEnoughSwitchResource(link.srcID, expectedTCAM),
            #         self._dib.hasEnoughSwitchResource(link.dstID, expectedTCAM)
            #     ))
            if (self._dib.isServerID(link.srcID) 
                    or self._dib.isServerID(link.dstID)):
                continue
            if ((self._dib.hasEnoughLinkResource(link, expectedBandwidth,
                    self.zoneName) 
                and self._dib.hasEnoughSwitchResource(link.srcID,
                    expectedTCAM, self.zoneName)
                and self._dib.hasEnoughSwitchResource(link.dstID,
                    expectedTCAM, self.zoneName)
                ) or (  not capacityAwareFlag  )):
                if not self._isAbandonLink(link):
                    edgeList.append((srcLayerNodeID, dstLayerNodeID, weight))
            else:
                self.logger.warning(
                    "Link {0}->{1} hasn't enough resource.".format(
                        link.srcID, link.dstID
                    ))
        G.add_weighted_edges_from(edgeList)

        # self.logger.debug("A layer graph nodes:{0}".format(G.nodes))
        # self.logger.debug("A layer graph edges:{0}".format(G.edges))
        # self.logger.debug("edges number:{0}".format(len(G.edges)))

        connectionFlag = nx.is_weakly_connected(copy.deepcopy(G))
        if connectionFlag == False:
            self.logger.debug("is_connected:{0}".format(connectionFlag))
            # nx.draw(G, with_labels=True)
            # plt.savefig("./temp.png")
            # plt.show()
            # raw_input()

        return G

    def _getExpectedBandwidth(self, stage):
        trafficDemand = self.sfc.getSFCTrafficDemand()
        return (stage+1) * trafficDemand

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
        pM = PerformanceModel()
        return pM.getPropogationLatency(link.linkLength)

    def _getLinkLatency(self, link, linkUtil):
        pM = PerformanceModel()
        return pM.getLatencyOfLink(link, linkUtil)

    def _connectLayersInMLG(self, mLG):
        for stage in range(self.sfcLength):
            self._connectLayer(mLG, stage, stage+1)

    def _connectLayer(self, mLG, layer1Num, layer2Num):
        switches = self._getSupportVNFSwitchesOfLayer(layer1Num)
        # self.logger.debug("switches:{0}".format(switches))
        # self.logger.debug("connect layer")
        for switch in switches:
            nodeID = switch.switchID
            (expectedCores, expectedMemory, expectedBandwidth) \
                = self._getExpectedServerResource(layer1Num)
            # self.logger.debug(
            #     "expected Cores:{0}, Memory:{1}, bandwdith:{2}".format(
            #         expectedCores, expectedMemory, expectedBandwidth
            # ))
            srcLayerNodeID = self._genLayerNodeID(nodeID, layer1Num)
            dstLayerNodeID = self._genLayerNodeID(nodeID, layer2Num)
            link = Link(srcLayerNodeID, dstLayerNodeID)
            if self._dib.hasEnoughNPoPServersResources(
                    nodeID, expectedCores, expectedMemory, expectedBandwidth,
                        self.zoneName, self.abandonNodeIDList):
                weight = self.getLinkWeight(link, isConnectingLink=True)
                # self.logger.debug("weight:{0}".format(weight))
                # raw_input()
                mLG.add_edge(srcLayerNodeID, dstLayerNodeID, weight=weight)
            else:
                self.logger.warning(
                    "NPoP {0} hasn't enough server resource.".format(
                        nodeID
                    ))

    def _getSupportVNFSwitchesOfLayer(self, layerNum):
        switches = []
        vnfType = self.sfc.vNFTypeSequence[layerNum]
        for switchID,switchInfoDict in self._dib.getSwitchesByZone(self.zoneName).items():
            switch = switchInfoDict['switch']
            if vnfType in switch.supportVNF:
                switches.append(switch)
        return switches

    def _getExpectedServerResource(self, layerNum):
        vnfType = self.sfc.vNFTypeSequence[layerNum]
        trafficDemand = self.sfc.getSFCTrafficDemand()
        pM = PerformanceModel()
        return pM.getExpectedServerResource(vnfType, trafficDemand)

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
        # raw_input()
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
