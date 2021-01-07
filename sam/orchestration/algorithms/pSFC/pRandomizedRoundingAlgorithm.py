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
from sam.serverController.serverManager.serverManager import *
from sam.orchestration.algorithms.multiLayerGraph import *
from sam.orchestration.algorithms.oPSFC.opRandomizedRoundingAlgorithm import *
from sam.orchestration.algorithms.base.mappingAlgorithmBase import *


class PRandomizedRoundingAlgorithm(OPRandomizedRoundingAlgorithm):
    def __init__(self, dib, requestList, pLP, requestForwardingPathSet):
        self._dib = dib
        self.requestList = requestList
        self.pLP = pLP
        self.requestForwardingPathSet = requestForwardingPathSet

        logConfigur = LoggerConfigurator(__name__, './log',
            'P-RRA.log', level='warning')
        self.logger = logConfigur.getLogger()

    def mapSFCI(self):
        self.logger.info("PRandomizedRoundingAlgorithm mapSFCI")
        self.init()
        self.randomizedRoundingAlgorithm()

    def init(self):
        self.jointLink = self.pLP.jointLinkSolution
        self.requestPartialPath = self.pLP.requestPartialPath
        self.requestPartialPathRIndex = self.pLP.requestPartialPathRIndex
        self.requestPartialPathBp = self.pLP.requestPartialPathBp
        self.requestPartialPathXp = self.pLP.requestPartialPathXp
        self.requestPartialPathSrcSwitchID = self.pLP.requestPartialPathSrcSwitchID
        self.requestPartialPathDstSwitchID = self.pLP.requestPartialPathDstSwitchID

    def randomizedRoundingAlgorithm(self):
        # p = (sp, bp, tp, Xp, lp)
        for pIndex in self.requestPartialPath:
            self._initPartialPathCalculation(pIndex)
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
            path = self._selectNPoPNodeAndServers(path)
            self._addPath2Sfci(path)
            self._updateResource(path)

    def _initPartialPathCalculation(self, pIndex):
        self.logger.debug(
            "randomizedRoundingAlgorithm for partial path:{0}".format(pIndex))
        self._pIndexInRRA = pIndex
        self._rIndexInRRA = self.requestPartialPathRIndex[pIndex]
        self._requestInRRA = self.requestList[self._rIndexInRRA]
        self.request = self._requestInRRA
        sfc = self._requestInRRA.attributes['sfc']
        self.zoneName = sfc.attributes['zone']
        self._candidatePathSet = {} # "(pIndex, i, j, u, v)": candidatePath

    def _existJointLinkLeq0(self):
        # self.logger.debug(
        #   "number of jointLink:{0}".format(len(self.jointLink)))
        for jointLink, value in self.jointLink.items():
            pIndex = jointLink[0]
            # self.logger.debug(
            #   "jointLink:{0}, value:{1}".format(jointLink, value))
            if value > 0 and pIndex == self._pIndexInRRA:
                return True

    def _selectJointLink(self):
        jointLinkList = [(jointLink, value) 
            for jointLink, value in self.jointLink.items() 
            if value > 0 and jointLink[0] == self._pIndexInRRA]
        return min(jointLinkList)

    def _findCandidatePath(self, jointLink):
        # self.logger.debug("opSFC: _findCandidatePath")
        (pIndex, i, j, u, v) = jointLink[0]
        if pIndex != self._pIndexInRRA:
            raise ValueError(
                "pIndex:{0} != self._pIndexInRRA:{1}".format(
                    pIndex, self._pIndexInRRA
                ))

        mlg = MultiLayerGraph()
        mlg.loadInstance4dibAndRequest(self._dib, 
            self._requestInRRA, WEIGHT_TYPE_01_UNIFORAM_MODEL)
        bp = self.requestPartialPathBp[pIndex]
        mlg.addAbandonNodeIDs([bp])
        mlg.addAbandonLinkIDs([])
        mlg.trans2MLG()

        startSwitchID = self.requestPartialPathSrcSwitchID[pIndex]
        sfc = self._requestInRRA.attributes['sfc']
        vnfLayerNum = mlg.getVnfLayerNumOfBackupVNF(i, j, sfc)
        Xp = self.requestPartialPathXp[pIndex]
        (startLayerNum, endLayerNum) = mlg.getStartAndEndlayerNum(Xp, sfc)
        self.logger.debug("startLayerNum:{0}, endLayerNum:{1}".format(startLayerNum, endLayerNum))
        firstHalfPath = mlg.getPath(vnfLayerNum, startSwitchID, vnfLayerNum, u)

        middleLinkPath = mlg.getPath(
            vnfLayerNum, u, vnfLayerNum, v)

        c = sfc.getSFCLength()
        endSwitchID = self.requestPartialPathDstSwitchID[pIndex]
        pathLatterHalf = mlg.getPath(
            vnfLayerNum, v, endLayerNum, endSwitchID)

        path = mlg.catPath(firstHalfPath, middleLinkPath)
        path = mlg.catPath(path, pathLatterHalf)
        path = mlg.deLoop(path)

        self.logger.debug("path:{0}".format(path))

        return path

    def _updateJointLinkValue(self, jointLink):
        minusValue = self.jointLink[jointLink[0]]
        for jointLink, value in self.jointLink.items():
            pIndex = jointLink[0]
            if value > 0 and pIndex == self._pIndexInRRA:
                self.jointLink[jointLink] = value - minusValue
                # self.logger.debug("updateJointLinkValue:{0}".format(
                #     self.jointLink[jointLink]
                # ))

    def _selectNPoPNodeAndServers(self, path):
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

        dividedPath = self._dividePath(path)

        # # add start node and end node
        startNodeID = self.requestPartialPathSrcSwitchID[self._pIndexInRRA]
        endNodeID = self.requestPartialPathDstSwitchID[self._pIndexInRRA]
        # dividedPath = self._addStartNodeIDAndEndNodeID2Path(dividedPath, startNodeID, endNodeID)

        # select a server for each stage
        serverList = self._selectServer4EachStage(dividedPath)
        dividedPath = self._addNFVI2Path(dividedPath, serverList)
        self.logger.info("startNodeID:{0}, endNodeID:{1}, dividedPath:{2}".format(
                startNodeID, endNodeID, dividedPath))

        return dividedPath

    def _selectServer4EachStage(self, dividedPath):
        Xp = self.requestPartialPathXp[self._pIndexInRRA]
        sfc = self._requestInRRA.attributes['sfc']
        trafficDemand = sfc.getSFCTrafficDemand()
        serverList = []
        for index in range(len(Xp)):
            vnfType = sfc.vNFTypeSequence[index]
            switchID = dividedPath[index][-1][1]
            self.logger.debug("switchID:{0}".format(switchID))
            servers = self._dib.getConnectedNFVIs(switchID, self.zoneName)
            server = self._selectServer4ServerList(servers, vnfType, trafficDemand)
            serverList.append(server)
            self.logger.debug("selected serverID: {0}".format(server.getServerID()))
        return serverList

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
        bp = self.requestPartialPathBp[self._pIndexInRRA]
        Xp = self.requestPartialPathXp[self._pIndexInRRA]
        xp = Xp[0]
        mlg = MultiLayerGraph()
        sfc = self._requestInRRA.attributes['sfc']
        vnfLayerNum = mlg.getVnfLayerNum(xp, sfc)
        self.requestForwardingPathSet[self._rIndexInRRA].backupForwardingPath[1][((vnfLayerNum, bp),'*')] = path
