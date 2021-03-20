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
from sam.orchestration.algorithms.base.pathServerFiller import *
from sam.orchestration.algorithms.base.mappingAlgorithmBase import *
from sam.orchestration.algorithms.base.multiLayerGraph import *


class OPRandomizedRoundingAlgorithm(MappingAlgorithmBase, PathServerFiller):
    def __init__(self, dib, requestList, opLP):
        self._dib = dib
        self.requestList = requestList
        self.opLP = opLP

        logConfigur = LoggerConfigurator(__name__, './log',
            'OP-RRA.log', level='debug')
        self.logger = logConfigur.getLogger()

    def mapSFCI(self):
        self.logger.info("OPRandomizedRoundingAlgorithm mapSFCI")
        self.init()
        self.randomizedRoundingAlgorithm()

    def init(self):
        self.jointLink = self.opLP.jointLinkSolution
        self.requestIngSwitchID = self.opLP.requestIngSwitchID
        self.requestEgSwitchID = self.opLP.requestEgSwitchID
        self.forwardingPathSetsDict = {}

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
            if existedPathFlag == False:
                raise ValueError(
                    "There are no candidate path"
                    " at all for rIndex:{0}.".format(rIndex))
            path = self._selectPath4Candidates()
            path = self._selectNPoPNodeAndServers(path, self._rIndexInRRA)
            self._addPath2Sfci(path)
            # Randomized Rounding Algorithm doesn't reserve resource
            # self._allocateResource(path)

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
        mlg.loadInstance4dibAndRequest(self._dib, self._requestInRRA,
            # WEIGHT_TYPE_0100_UNIFORAM_MODEL)
            # WEIGHT_TYPE_CONST)

            WEIGHT_TYPE_CONST,
            WEIGHT_TYPE_0100_UNIFORAM_MODEL)
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
        self.logger.debug("_candidatePathSet:{0}".format(
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

    def _addPath2Sfci(self, path):
        forwardingPath = path
        primaryForwardingPath = {1:forwardingPath}
        mappingType = MAPPING_TYPE_NOTVIA_PSFC
        backupForwardingPath = {1:{}}
        self.forwardingPathSetsDict[self._rIndexInRRA] = ForwardingPathSet(
            primaryForwardingPath, mappingType, backupForwardingPath)
