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
from sam.orchestration.algorithms.base.multiLayerGraph import *
from sam.orchestration.algorithms.oPSFC.opRandomizedRoundingAlgorithm import *
from sam.orchestration.algorithms.base.mappingAlgorithmBase import *


class PRandomizedRoundingAlgorithm(OPRandomizedRoundingAlgorithm):
    def __init__(self, dib, requestList, pLP, forwardingPathSetsDict):
        self._initDib = copy.deepcopy(dib)
        self._dibDict = {}
        self._dib = None
        self.requestList = requestList
        self.pLP = pLP
        self.forwardingPathSetsDict = forwardingPathSetsDict

        logConfigur = LoggerConfigurator(__name__, './log',
            'P-RRA.log', level='debug')
        self.logger = logConfigur.getLogger()

    def getDibDict(self):
        return self._dibDict

    def mapSFCI(self):
        self.logger.info("PRandomizedRoundingAlgorithm mapSFCI")
        self.init()
        self.randomizedRoundingAlgorithm()

    def init(self):
        self.jointLink = self.pLP.jointLinkSolution
        self.vnfDeployment = self.pLP.vnfDeploymentSolution
        self.requestPartialPath = self.pLP.requestPartialPath
        self.requestPartialPathRIndex = self.pLP.requestPartialPathRIndex
        self.requestPartialPathBp = self.pLP.requestPartialPathBp
        self.requestPartialPathXp = self.pLP.requestPartialPathXp
        self.requestPartialPathSrcSwitchID = self.pLP.requestPartialPathSrcSwitchID
        self.requestPartialPathDstSwitchID = self.pLP.requestPartialPathDstSwitchID

        for pIndex in self.requestPartialPath:
            bp = self.requestPartialPathBp[pIndex]
            # print(bp)
            # print(type(bp))
            # raw_input()
            self._dibDict[bp] = copy.deepcopy(self._initDib)

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
                self.logger.debug("findCandidatePath:{0}".format(path))
                self._addCandidatePath(jointLink, path)
                self._updateJointLinkValue(jointLink)
            self.logger.debug("existedPathFlag:{0}".format(existedPathFlag))
            if existedPathFlag == False:
                # raise ValueError(
                #     "There are no candidate path"
                #     " at all for pIndex:{0}.".format(pIndex))
                self.logger.warning(
                    "There are no candidate path"
                    " at all for pIndex:{0}.".format(pIndex)
                )
                path = self._getCandidatePath4NoneJointLink(pIndex)
            else:
                path = self._selectPath4Candidates()
            path = self._selectNPoPNodeAndServers(path, self._pIndexInRRA)
            self._addPath2Sfci(path)
            # Randomized Rounding Algorithm doesn't reserve resource
            # self._allocateResource(path)

    def _getCandidatePath4NoneJointLink(self, pathIndex):
        rIndex = self.requestPartialPathRIndex[pathIndex]
        sfc = self.requestList[rIndex].attributes['sfc']
        vnfSeq = sfc.vNFTypeSequence

        vnfSwitchIDTupleDict = self._getVNFSwitchIDTupleDict(pathIndex)
        layerNumVNFSwitchIDTupleList = self._getLayerNumVNFSwitchIDTupleList(
            vnfSeq, vnfSwitchIDTupleDict)
        path = []
        for layerNumVNFSwitchIDTuple in layerNumVNFSwitchIDTupleList:
            (vnfLayerNum, vnfType, switchID) = layerNumVNFSwitchIDTuple
            path.append((vnfLayerNum, switchID))
            maxVnfLayerNum = vnfLayerNum

        tp = self.requestPartialPathDstSwitchID[pathIndex]
        path.append((maxVnfLayerNum+1, tp))

        self.logger.debug("none joint link candidate path:{0}".format(path))
        # raw_input()

        return path

    def _getVNFSwitchIDTupleDict(self, pathIndex):
        vnfSwitchIDTupleDict = {}
        for key in self.vnfDeployment.keys():
            if self.vnfDeployment[key] >= 1:
                (pIndex, vnf, switchID) = key
                if pIndex == pathIndex:
                    if vnf not in vnfSwitchIDTupleDict.keys():
                        vnfSwitchIDTupleDict[vnf] = switchID
                    else:
                        self.logger.error("Invalid vnfDeployment variable for"
                            "pIndex:{0} vnf:{1} @ switchID:{2}".format(
                                pIndex, vnf, switchID))
                        raise ValueError("Invalid vnfDeployment vairable")
        return vnfSwitchIDTupleDict

    def _getLayerNumVNFSwitchIDTupleList(self, vnfSeq, vnfSwitchIDTupleDict):
        layerNumVNFSwitchIDTupleList = []
        vnfLayerNum = 0
        for vnfType in vnfSeq:
            vnfLayerNum = vnfLayerNum + 1
            if vnfType in vnfSwitchIDTupleDict.keys():
                switchID = vnfSwitchIDTupleDict[vnfType]
                layerNumVNFSwitchIDTupleList.append((vnfLayerNum, vnfType,
                    switchID))
        return layerNumVNFSwitchIDTupleList

    def _initPartialPathCalculation(self, pIndex):
        self.logger.debug(
            "randomizedRoundingAlgorithm for partial path:{0}".format(pIndex))
        self._pIndexInRRA = pIndex
        bp = self.requestPartialPathBp[pIndex]
        self._dib = self._dibDict[bp]
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
            self._requestInRRA, 
            WEIGHT_TYPE_0100_UNIFORAM_MODEL)
            # WEIGHT_TYPE_CONST)
        bp = self.requestPartialPathBp[pIndex]
        mlg.addAbandonNodeIDs([bp])
        mlg.addAbandonLinkIDs([])
        mlg.trans2MLG()

        startSwitchID = self.requestPartialPathSrcSwitchID[pIndex]
        sfc = self._requestInRRA.attributes['sfc']
        vnfLayerNum = mlg.getVnfLayerNumOfBackupVNF(i, j, sfc)
        Xp = self.requestPartialPathXp[pIndex]
        (startLayerNum, endLayerNum) = mlg.getStartAndEndlayerNum(Xp, sfc)
        # self.logger.debug("Xp:{0}, sfc:{1}, i:{2}, j:{3}".format(
        #     Xp, sfc, i, j))
        self.logger.debug("startLayerNum:{0}, endLayerNum:{1}".format(
            startLayerNum, endLayerNum))
        firstHalfPath = mlg.getPath(startLayerNum, startSwitchID,
            vnfLayerNum, u)

        middleLinkPath = mlg.getPath(vnfLayerNum, u, vnfLayerNum, v)

        c = sfc.getSFCLength()
        endSwitchID = self.requestPartialPathDstSwitchID[pIndex]
        pathLatterHalf = mlg.getPath(vnfLayerNum, v, endLayerNum, endSwitchID)

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

    def _selectNPoPNodeAndServers(self, path, pIndex):
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
        startNodeID = self.requestPartialPathSrcSwitchID[pIndex]
        endNodeID = self.requestPartialPathDstSwitchID[pIndex]
        # dividedPath = self._addStartNodeIDAndEndNodeID2Path(dividedPath, startNodeID, endNodeID)

        # select a server for each stage
        serverList = self._selectNFVI4EachStage(dividedPath, pIndex)
        dividedPath = self._addNFVI2Path(dividedPath, serverList)
        self.logger.info("startNodeID:{0}, endNodeID:{1}, dividedPath:{2}".format(
                startNodeID, endNodeID, dividedPath))

        return dividedPath

    def _selectNFVI4EachStage(self, dividedPath, pIndex):
        sp = self.requestPartialPathSrcSwitchID[pIndex]
        bp = self.requestPartialPathBp[pIndex]
        tp = self.requestPartialPathDstSwitchID[pIndex]
        Xp = self.requestPartialPathXp[pIndex]
        sfc = self._requestInRRA.attributes['sfc']
        vnfSeq = sfc.vNFTypeSequence
        trafficDemand = sfc.getSFCTrafficDemand()
        serverList = []
        for index in range(len(dividedPath)-1):
            vnfType = Xp[index]
            switchID = dividedPath[index][-1][1]
            self.logger.debug(
                "sp:{0}\nbp:{1}\ntp:{2}\nXp:{3}\nvnfSeq:{4}".format(
                    sp, bp, tp, Xp, vnfSeq))
            self.logger.debug("dividedPath:{0}".format(dividedPath))
            self.logger.debug("switchID:{0}".format(switchID))
            if len(Xp) != len(dividedPath)-1:
                self.logger.error("length error")
                raise ValueError(
                    "length of Xp {0} != length of dividedPath-1 {1}".format(
                        len(Xp), len(dividedPath)-1))
            servers = self._dib.getConnectedNFVIs(switchID, self.zoneName)
            # self.logger.debug("servers:{0}".format(servers))
            server = self._selectServer4ServerList(servers, vnfType,
                trafficDemand)
            serverList.append(server)
            self.logger.debug("selected serverID: {0}".format(
                server.getServerID()))
        return serverList

    def _addPath2Sfci(self, path):
        bp = self.requestPartialPathBp[self._pIndexInRRA]
        Xp = self.requestPartialPathXp[self._pIndexInRRA]
        xp = Xp[0]
        mlg = MultiLayerGraph()
        sfc = self._requestInRRA.attributes['sfc']
        vnfLayerNum = mlg.getVnfLayerNum(xp, sfc)
        requstFPSet = self.forwardingPathSetsDict[self._rIndexInRRA]
        self.backupForwardingPath = requstFPSet.backupForwardingPath[1]
        self.backupForwardingPath[
                (
                    ("failureNPoPID", (vnfLayerNum, bp, Xp)),
                    ("repairMethod", "increaseBackupPathPrioriy")
                )
            ] = path
