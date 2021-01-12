#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
original sfc mapping
[2018][globecom]Partial Rerouting for High-Availability and
Low-Cost Service Function Chain
'''

import copy

import numpy as np
import gurobipy as gp
from gurobipy import *
from gurobipy import GRB

from sam.base.path import *
from sam.base.server import *
from sam.base.messageAgent import *
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.orchestration.algorithms.multiLayerGraph import *
from sam.orchestration.algorithms.base.mappingAlgorithmBase import *


class OPRandomizedRoundingAlgorithm(MappingAlgorithmBase):
    def __init__(self, dib, requestList, opLP):
        self._dib = dib
        self.requestList = requestList
        self.opLP = opLP

        logConfigur = LoggerConfigurator(__name__, './log',
            'OP-RRA.log', level='warning')
        self.logger = logConfigur.getLogger()

    def mapSFCI(self):
        self.logger.info("OPRandomizedRoundingAlgorithm mapSFCI")
        self.init()
        self.randomizedRoundingAlgorithm()

    def init(self):
        self.jointLink = self.opLP.jointLinkSolution
        self.requestIngSwitchID = self.opLP.requestIngSwitchID
        self.requestEgSwitchID = self.opLP.requestEgSwitchID
        self.requestForwardingPathSet = {}

    def randomizedRoundingAlgorithm(self):
        for rIndex in range(len(self.requestList)):
            self._initRequestCalculation(rIndex)
            existedPathFlag = False
            while self._existJointLinkLeq0():
                existedPathFlag = True
                jointLink = self._selectJointLink()
                # self.logger.debug("jointLink:{0}".format(jointLink))
                path = self._findCandidatePath(jointLink)
                # self.logger.debug("findCandidatePath:{0}".format(path))
                self._addCandidatePath(jointLink, path)
                self._updateJointLinkValue(jointLink)
            self.logger.debug("existedPathFlag:{0}".format(existedPathFlag))
            path = self._selectPath4Candidates()
            path = self._selectNPoPNodeAndServers(path, self._rIndexInRRA)
            self._addPath2Sfci(path)
            self._updateResource(path)

    def _initRequestCalculation(self, rIndex):
        self.logger.debug(
            "randomizedRoundingAlgorithm for request:{0}".format(rIndex))
        self._rIndexInRRA = rIndex
        self._requestInRRA = self.requestList[rIndex]
        self.request = self._requestInRRA
        sfc = self._requestInRRA.attributes['sfc']
        self.zoneName = sfc.attributes['zone']
        self._candidatePathSet = {} # "(rIndex, i, j, u, v)": candidatePath

    def _existJointLinkLeq0(self):
        # self.logger.debug(
        #   "number of jointLink:{0}".format(len(self.jointLink)))
        for jointLink, value in self.jointLink.items():
            rIndex = jointLink[0]
            # self.logger.debug(
            #   "jointLink:{0}, value:{1}".format(jointLink, value))
            if value > 0 and rIndex == self._rIndexInRRA:
                return True

    def _selectJointLink(self):
        jointLinkList = [(jointLink, value) 
            for jointLink, value in self.jointLink.items() 
            if value > 0 and jointLink[0] == self._rIndexInRRA]
        return min(jointLinkList)

    def _findCandidatePath(self, jointLink):
        # self.logger.debug("opSFC: _findCandidatePath")
        (rIndex, i, j, u, v) = jointLink[0]
        if rIndex != self._rIndexInRRA:
            raise ValueError("rIndex != self._rIndexInRRA")

        mlg = MultiLayerGraph()
        mlg.loadInstance4dibAndRequest(self._dib, 
            self._requestInRRA, WEIGHT_TYPE_01_UNIFORAM_MODEL)
        mlg.addAbandonNodeIDs([])
        mlg.addAbandonLinkIDs([])
        mlg.trans2MLG()

        ingSwitchID = self.requestIngSwitchID[rIndex]
        sfc = self._requestInRRA.attributes['sfc']
        vnfLayerNum = mlg.getVnfLayerNum(i, sfc)
        firstHalfPath = mlg.getPath(0, ingSwitchID, vnfLayerNum, u)

        middleLinkPath = mlg.getPath(
            vnfLayerNum, u, vnfLayerNum, v)

        c = sfc.getSFCLength()
        egSwitchID = self.requestEgSwitchID[rIndex]
        pathLatterHalf = mlg.getPath(
            vnfLayerNum, v, c, egSwitchID)

        path = mlg.catPath(firstHalfPath, middleLinkPath)
        path = mlg.catPath(path, pathLatterHalf)
        path = mlg.deLoop(path)

        return path

    def _addCandidatePath(self, jointLink, path):
        self._candidatePathSet[jointLink] = path

    def _updateJointLinkValue(self, jointLink):
        minusValue = self.jointLink[jointLink[0]]
        for jointLink, value in self.jointLink.items():
            rIndex = jointLink[0]
            if value > 0 and rIndex == self._rIndexInRRA:
                self.jointLink[jointLink] = value - minusValue
                # self.logger.debug("updateJointLinkValue:{0}".format(
                #     self.jointLink[jointLink]
                # ))

    def _selectPath4Candidates(self):
        pathNameList = []
        probabilityList = []
        pathNameMapTable = {}
        self.logger.debug("self._candidatePathSet:{0}".format(
            self._candidatePathSet
        ))
        for jointLink,path in self._candidatePathSet.items():
            probability = jointLink[1]
            probabilityList.append(probability)
            pathName = self._getPathName(jointLink)
            pathNameList.append(pathName)
            pathNameMapTable[pathName] = path

        pathTuple = tuple(pathNameList)
        probabilityList = tuple(probabilityList)

        self.logger.debug("pathTuple:{0}".format(pathTuple))
        self.logger.debug("probabilityList:{0}".format(probabilityList))

        norm = tuple([float(i)/sum(probabilityList) for i in probabilityList])

        pathName = np.random.choice(pathTuple, size=1, replace=True, p=norm)[0]

        # self.logger.debug("pathName:{0}".format(pathName))
        # self.logger.debug(
        #     "pathNameMapTable[pathName]:{0}".format(
        #         pathNameMapTable[pathName]))

        return pathNameMapTable[pathName]

    def _getPathName(self, jointLink):
        name = ""
        for index in range(len(jointLink[0])):
            name = name + str(jointLink[0][index]) + "_"
        return name

    def _selectNPoPNodeAndServers(self, path, rIndex):
        self.logger.debug("path: {0}".format(path))
        # Example 1
        # before adding servers
        # [(0, 13), (0, 5), (0, 3), (0, 11), (0, 19), (1, 19), (2, 19), (3, 19)]
        # after adding servers
        # [
        # [(0, 10001), (0, 13), (0, 5), (0, 3), (0, 11), (0, 19), (0, 10002)],
        # [(1, 10002), (1, 19), (1, 10002)],
        # [(2, 10002), (2, 19), (2, 10004)],
        # [(3, 10004), (3, 19), (3, 10003)]
        # ]

        # Example 2
        # before adding servers
        # [(0, 15), (0, 6), (0, 14), (1, 14), (1, 6), (1, 0), (1, 8), (1, 16)]
        # after adding servers
        # [
        # [(0, 10001), (0, 15), (0, 6), (0, 14), (0, 10002)],
        # [(1, 10002), (1, 14), (1, 6), (1, 0), (1, 8), (1, 16), (1, 10003)]
        # ]

        request = self.requestList[rIndex]

        dividedPath = self._dividePath(path)

        # add ingress and egress
        ingID = self._getIngressID(request)
        egID = self._getEgressID(request)
        dividedPath = self._addStartNodeIDAndEndNodeID2Path(dividedPath, ingID, egID)

        # select a server for each stage
        serverList = self._selectServer4EachStage(dividedPath, request)
        dividedPath = self._addNFVI2Path(dividedPath, serverList)
        self.logger.info("ingID:{0}, egID:{1}, dividedPath:{2}".format(
                ingID, egID, dividedPath))

        return dividedPath

    def _dividePath(self, path):
        pathSegment = {}
        for node in path:
            stage = node[0]
            nodeID = node[1]
            if stage not in pathSegment.keys():
                pathSegment[stage] = []
            pathSegment[stage].append(node)

        dividedPath = []
        for stage in pathSegment.keys():
            dividedPath.append(pathSegment[stage])
        self.logger.debug("dividedPath:{0}".format(dividedPath))
        return dividedPath

    def _getIngressID(self, request):
        sfc = request.attributes['sfc']
        ingress = sfc.directions[0]['ingress']
        return ingress.getServerID()

    def _getEgressID(self, request):
        sfc = request.attributes['sfc']
        egress = sfc.directions[0]['egress']
        return egress.getServerID()

    def _addStartNodeIDAndEndNodeID2Path(self, dividedPath, startNodeID, endNodeID):
        dividedPath[0].insert(0, (0, startNodeID))
        dividedPath[-1].append((len(dividedPath)-1, endNodeID))
        self.logger.debug("add start and end node to dividedPath:{0}".format(dividedPath))
        return dividedPath

    def _selectServer4EachStage(self, dividedPath, request):
        sfc = request.attributes['sfc']
        trafficDemand = sfc.getSFCTrafficDemand()
        c = sfc.getSFCLength()
        serverList = []
        for index in range(c):
            vnfType = sfc.vNFTypeSequence[index]
            switchID = dividedPath[index][-1][1]
            self.logger.debug("switchID:{0}".format(switchID))
            servers = self._dib.getConnectedNFVIs(switchID, self.zoneName)
            server = self._selectServer4ServerList(servers, vnfType, trafficDemand)
            serverList.append(server)
        return serverList

    def _selectServer4ServerList(self, serverList, vnfType, trafficDemand):
        # First-fit algorithm
        for server in serverList:
            if self._hasEnoughResource(server, vnfType, trafficDemand):
                return server

    def _hasEnoughResource(self, server, vnfType, trafficDemand):
        pM = PerformanceModel()
        (expectedCores, expectedMemory, expectedBandwidth) = pM.getExpectedServerResource(
            vnfType, trafficDemand)
        serverID = server.getServerID()
        return self._dib.hasEnoughServerResources(
            serverID, (expectedCores, expectedMemory, expectedBandwidth), self.zoneName)

    def _addNFVI2Path(self, dividedPath, serverList):
        # self.logger.debug("dividedPath:{0}".format(dividedPath))
        # for server in serverList:
        #     self.logger.debug("serverID:{0}".format(server.getServerID()))

        for index in range(len(serverList)):
            currentIndex = index
            nextIndex = index + 1
            serverID = serverList[currentIndex].getServerID()
            dividedPath[currentIndex].append((currentIndex,serverID))
            dividedPath[nextIndex].insert(0, (nextIndex, serverID))
        self.logger.debug("new dividedPath:{0}".format(dividedPath))
        return dividedPath

    def _addPath2Sfci(self, path):
        forwardingPath = path
        primaryForwardingPath = {1:forwardingPath}
        mappingType = MAPPING_TYPE_NOTVIA_PSFC
        backupForwardingPath = {1:{}}
        self.requestForwardingPathSet[self._rIndexInRRA] = ForwardingPathSet(
            primaryForwardingPath, mappingType, backupForwardingPath)
