#!/usr/bin/python
# -*- coding: UTF-8 -*-

import copy
import math

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


class MultiLayerGraph(object):
    def __init__(self):
        logConfigur = LoggerConfigurator(__name__, './log',
            'MultiLayerGraph.log', level='debug')
        self.logger = logConfigur.getLogger()

    def loadInstance4dibAndRequest(self, dib, request, weightType):
        self._dib = dib
        self.request = request
        self.sfc = request.attributes['sfc']
        self.sfcLength = self._getRequestSFCLength(request)
        self.zoneName = self.sfc.attributes['zone']
        self.weightType = weightType

    def _getRequestSFCLength(self, request):
        sfc = request.attributes['sfc']
        return len(sfc.vNFTypeSequence)

    def trans2MLG(self):
        gList = []
        for stage in range(self.sfcLength+1):
            g = self._genOneLayer(stage)
            gList.append(g)

        mLG = nx.compose_all(gList)
        self._connectLayersInMLG(mLG)
        self.multiLayerGraph = mLG

    def _genOneLayer(self, stage):
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
            #         self._hasEnoughLinkResource(link, expectedBandwidth),
            #         self._hasEnoughNodeResource(link.srcID, expectedTCAM),
            #         self._hasEnoughNodeResource(link.dstID, expectedTCAM)
            #     ))
            if (self._hasEnoughLinkResource(link, expectedBandwidth) and 
                self._hasEnoughNodeResource(link.srcID, expectedTCAM) and 
                self._hasEnoughNodeResource(link.dstID, expectedTCAM)
                ):
                e.append((s,d,weight))
            else:
                self.logger.warning(
                    "Link {0}->{1} hasn't enough resource.".format(
                        link.srcID, link.dstID
                    ))
        G.add_weighted_edges_from(e)

        self.logger.debug("A layer graph nodes:{0}".format(G.nodes))
        # self.logger.debug("A layer graph edges:{0}".format(G.edges))
        # self.logger.debug("edges number:{0}".format(len(G.edges)))

        return G

    def _getExpectedBandwidth(self, stage):
        trafficDemand = self.sfc.slo.throughput
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
        else:
            raise ValueError("Unknown weight type.")

    def _getLinkUtil(self, link):
        reservedBandwidth = self._dib.getLinkReservedResource(
            link.srcID, link.dstID, self.zoneName)
        bandwidth = link.bandwidth
        return reservedBandwidth*1.0/bandwidth

    def _getLinkLatency(self, link, linkUtil):
        lm = PerformanceModel()
        return lm.getLatencyOfLink(link, linkUtil)

    def _hasEnoughLinkResource(self, link, expectedBandwidth):
        reservedBandwidth = self._dib.getLinkReservedResource(
            link.srcID, link.dstID, self.zoneName)
        bandwidth = link.bandwidth
        residualBandwidth = bandwidth - reservedBandwidth
        # self.logger.debug(
        #     "link resource, bandwidth:{0}, reservedBandwidth:{1}, expectedBandwidth:{2}".format(
        #         bandwidth, reservedBandwidth,expectedBandwidth
        #     ))
        if residualBandwidth > expectedBandwidth:
            return True
        else:
            return False

    def _hasEnoughNodeResource(self, nodeID, expectedTCAM):
        # TCAM resources
        switch = self._dib.getSwitch(nodeID, self.zoneName)
        tCAMCapacity = switch.tcamSize
        reservedTCAM = self._dib.getSwitchReservedResource(
            nodeID, self.zoneName)
        residualTCAM = tCAMCapacity - reservedTCAM
        # self.logger.debug(
        #     "node resource, tCAMCapacity:{0}, reservedTCAM:{1}, expectedTCAM:{2}".format(
        #         tCAMCapacity, reservedTCAM, expectedTCAM
        #     ))
        if residualTCAM > expectedTCAM:
            return True
        else:
            return False

    def _connectLayersInMLG(self, mLG):
        for stage in range(self.sfcLength):
            self._connectLayer(mLG, stage, stage+1)

    def _connectLayer(self, mLG, layer1Num, layer2Num):
        switches = self._getSupportVNFSwitchesOfLayer(layer1Num)
        for switch in switches:
            nodeID = switch.switchID
            (expectedCores, expectedMemory) = self._getExpectedServerResource(layer1Num)
            # self.logger.debug("expected Cores:{0}, Memory:{1}".format(
            #     expectedCores, expectedMemory
            # ))
            s = self._genNodeID(nodeID, layer1Num)
            d = self._genNodeID(nodeID, layer2Num)
            if self._hasEnoughServersResources(nodeID,
                                            expectedCores, expectedMemory):
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
        resConRatio = self._getResourceConsumeRatio(vnfType)
        trafficDemand = self.sfc.slo.throughput
        for index in range(len(resConRatio)):
            resConRatio[index] = math.ceil(
                resConRatio[index] * trafficDemand)
        return resConRatio

    def _getResourceConsumeRatio(self, vnfType):
        lm = PerformanceModel()
        return lm.getResourceConsumeRatioOfVNF(vnfType)

    def _hasEnoughServersResources(self, nodeID,
                                    expectedCores, expectedMemory):
        # cores and memory resources
        switch = self._dib.getSwitch(nodeID, self.zoneName)
        servers = self._dib.getConnectedServers(nodeID, self.zoneName)
        (coresSum, memorySum) = self._dib.getServersReservedResources(
            servers, self.zoneName)
        (coreCapacity, memoryCapacity) = self._dib.getServersResourcesCapacity(
            servers, self.zoneName)
        residualCores = coreCapacity - coresSum
        residualMemory = memoryCapacity - memorySum
        # self.logger.debug(
        #     "servers resource, residualCores:{0}, \
        #        residualMemory:{1}".format(
        #         residualCores, residualMemory
        #     ))
        if (residualCores > expectedCores 
            and residualMemory > expectedMemory):
            return True
        else:
            return False

    def getPath(self, startLayer, startNode, endLayer, endNode):
        pass

    def catPath(self, pathFirstHalf, pathMiddleLink):
        pass
