#!/usr/bin/python
# -*- coding: UTF-8 -*-

import copy
import math
import random

import networkx as nx
import gurobipy as gp
from gurobipy import *
from gurobipy import GRB

from sam.base.path import *
from sam.base.link import *
from sam.base.switch import *
from sam.base.server import *
from sam.base.messageAgent import *
from sam.base.socketConverter import *
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.orchestration.algorithms.performanceModel import *

WEIGHT_TYPE_CONST = "WEIGHT_TYPE_CONST"
WEIGHT_TYPE_DELAY_MODEL = "WEIGHT_TYPE_DELAY_MODEL"
WEIGHT_TYPE_01_UNIFORAM_MODEL = "WEIGHT_TYPE_01_UNIFORAM_MODEL"


class MultiLayerGraph(object):
    def __init__(self):
        logConfigur = LoggerConfigurator(__name__, './log',
            'MultiLayerGraph.log', level='debug')
        self.logger = logConfigur.getLogger()

    def loadInstance4dibAndRequest(self, dib, request, weightType):
        self._dib = dib
        self.request = request
        self.sfc = request.attributes['sfc']
        self.sfcLength = self.sfc.getSFCLength()
        self.zoneName = self.sfc.attributes['zone']
        self.weightType = weightType
        self.abandonNodeList = []
        self.abandonLinkList = []

    def addAbandonNodes(self, nodeIDList):
        for nodeID in nodeIDList:
            self.abandonNodeList = self.abandonNodeList + nodeIDList

    def addAbandonLinks(self, linkIDList):
        for link in linkIDList:
            self.abandonLinkList = self.abandonLinkList + linkIDList

    def trans2MLG(self):
        gList = []
        for stage in range(self.sfcLength+1):
            g = self.genOneLayer(stage)
            gList.append(g)

        mLG = nx.compose_all(gList)
        self._connectLayersInMLG(mLG)
        self.multiLayerGraph = mLG

    def genOneLayer(self, stage):
        G = nx.DiGraph()
        e = []

        expectedBandwidth = self._getExpectedBandwidth(stage)
        expectedTCAM = self._getExpectedTCAM(stage)

        linkDict = self._dib.getLinksByZone(self.zoneName)
        for link in linkDict.itervalues():
            s = self._genNodeID(link.srcID, stage)
            d = self._genNodeID(link.dstID, stage)
            weight = self._getLinkWeight(link)
            # self.logger.debug(
            #     "resource link:{0}, node1:{1}, node2:{2}".format(
            #         self._dib.hasEnoughLinkResource(link, expectedBandwidth),
            #         self._dib.hasEnoughSwitchResource(link.srcID, expectedTCAM),
            #         self._dib.hasEnoughSwitchResource(link.dstID, expectedTCAM)
            #     ))
            if (self._dib.hasEnoughLinkResource(link, expectedBandwidth, self.zoneName) 
                and self._dib.hasEnoughSwitchResource(link.srcID, expectedTCAM, self.zoneName)
                and self._dib.hasEnoughSwitchResource(link.dstID, expectedTCAM, self.zoneName)
                ):
                if not self._isAbandonLink(link):
                    e.append((s,d,weight))
            else:
                self.logger.warning(
                    "Link {0}->{1} hasn't enough resource.".format(
                        link.srcID, link.dstID
                    ))
        G.add_weighted_edges_from(e)

        # self.logger.debug("A layer graph nodes:{0}".format(G.nodes))
        # self.logger.debug("A layer graph edges:{0}".format(G.edges))
        # self.logger.debug("edges number:{0}".format(len(G.edges)))

        return G

    def _getExpectedBandwidth(self, stage):
        trafficDemand = self.sfc.getSFCTrafficDemand()
        return (stage+1) * trafficDemand

    def _getExpectedTCAM(self, stage):
        return stage+1

    def _genNodeID(self, nodeID, stage):
        return (stage, nodeID)

    def _getLinkWeight(self, link):
        if self.weightType == WEIGHT_TYPE_CONST:
            return 1
        elif self.weightType == WEIGHT_TYPE_DELAY_MODEL:
            linkUtil = self._getLinkUtil(link)
            return self._getLinkLatency(link, linkUtil)
        elif self.weightType == WEIGHT_TYPE_01_UNIFORAM_MODEL:
            # return 1
            return random.random()
        else:
            raise ValueError("Unknown weight type.")

    def _isAbandonLink(self, link):
        srcID = link.srcID
        dstID = link.dstID
        if ( link in self.abandonLinkList
            or srcID in self.abandonNodeList
            or dstID in self.abandonNodeList):
            return True
        else:
            return False

    def _getLinkUtil(self, link):
        reservedBandwidth = self._dib.getLinkReservedResource(
            link.srcID, link.dstID, self.zoneName)
        bandwidth = link.bandwidth
        return reservedBandwidth*1.0/bandwidth

    def _getLinkLatency(self, link, linkUtil):
        pM = PerformanceModel()
        return pM.getLatencyOfLink(link, linkUtil)

    def _connectLayersInMLG(self, mLG):
        for stage in range(self.sfcLength):
            self._connectLayer(mLG, stage, stage+1)

    def _connectLayer(self, mLG, layer1Num, layer2Num):
        switches = self._getSupportVNFSwitchesOfLayer(layer1Num)
        for switch in switches:
            nodeID = switch.switchID
            (expectedCores, expectedMemory, expectedBandwidth) = self._getExpectedServerResource(layer1Num)
            # self.logger.debug("expected Cores:{0}, Memory:{1}, bandwdith:{2}".format(
            #     expectedCores, expectedMemory, expectedBandwidth
            # ))
            s = self._genNodeID(nodeID, layer1Num)
            d = self._genNodeID(nodeID, layer2Num)
            if self._dib.hasEnoughNPoPServersResources(
                    nodeID, expectedCores, expectedMemory, expectedBandwidth, self.zoneName):
                mLG.add_edge(s, d, weight=0)

    def _getSupportVNFSwitchesOfLayer(self, layerNum):
        switches = []
        vnfType = self.sfc.vNFTypeSequence[layerNum]
        for switchID,switch in self._dib.getSwitchesByZone(self.zoneName).items():
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

        path = nx.dijkstra_path(self.multiLayerGraph,
            startNodeInMLG, endNodeInMLG)

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
