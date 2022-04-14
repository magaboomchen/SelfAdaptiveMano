#!/usr/bin/python
# -*- coding: UTF-8 -*-

import copy

import networkx as ax

from sam.base.path import *
from sam.base.server import *
from sam.base.messageAgent import *
from sam.base.socketConverter import SocketConverter, BCAST_MAC
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.orchestration.algorithms.pSFC.partialLP import *
from sam.orchestration.algorithms.pSFC.pRandomizedRoundingAlgorithm import *
from sam.orchestration.algorithms.base.multiLayerGraph import *
from sam.orchestration.algorithms.base.mappingAlgorithmBase import *


class NotVia(MappingAlgorithmBase):
    def __init__(self, dib, dibDict, requestList, forwardingPathSetsDict):
        self._initDib = copy.deepcopy(dib)
        self._dibDict = dibDict
        self._dib = None
        self.requestList = requestList
        self.forwardingPathSetsDict = forwardingPathSetsDict
        self.failureType = "node"

        logConfigur = LoggerConfigurator(__name__, './log',
            'NotVia.log', level='debug')
        self.logger = logConfigur.getLogger()

    def mapSFCI(self):
        self.logger.info("notVia mapSFCI")
        self.notVia()
        return self.forwardingPathSetsDict

    def notVia(self):
        for rIndex in self.forwardingPathSetsDict.keys():
            self.request = self.requestList[rIndex]
            sfc = self.request.attributes['sfc']
            self.zoneName = sfc.attributes['zone']
            self._initPathIDAssigner()
            fpSetDict = self.forwardingPathSetsDict[rIndex]
            self.primaryForwardingPath = fpSetDict.primaryForwardingPath[1]
            self.backupForwardingPath = fpSetDict.backupForwardingPath[1]
            for segPath in self.primaryForwardingPath:
                self._calByPassPaths4SegPath(segPath)

    def _initPathIDAssigner(self):
        self.pathID = 0

    def _assignPathID(self):
        self.pathID = self.pathID + 1
        return self.pathID

    def _calByPassPaths4SegPath(self, segPath):
        if self.failureType == "node":
            if len(segPath) < 5:
                return None

            for layerNodeID in segPath[2:-2]:
                index = segPath.index(layerNodeID)
                preIndex = index - 1
                nextIndex = index + 1

                stageNum = segPath[preIndex][0]
                startLayerNodeID = (0, segPath[preIndex][1])
                endLayerNodeID = (0, segPath[nextIndex][1])
                abandonNodeID = layerNodeID[1]
                abandonLayerNodeID = layerNodeID

                if abandonNodeID in self._dibDict.keys():
                    self._dib = self._dibDict[abandonNodeID]
                else:
                    self._dibDict[abandonNodeID] = copy.deepcopy(self._initDib)
                    self._dib = self._dibDict[abandonNodeID]

                if self._hasBackupPath(abandonLayerNodeID,
                            startLayerNodeID, endLayerNodeID):
                    continue

                mlg = MultiLayerGraph()
                mlg.loadInstance4dibAndRequest(self._dib, self.request,
                    WEIGHT_TYPE_CONST)
                    # WEIGHT_TYPE_0100_UNIFORAM_MODEL)
                mlg.addAbandonNodeIDs([abandonNodeID])
                graph = mlg.genOneLayer(0)
                try:
                    path = nx.dijkstra_path(graph, startLayerNodeID,
                        endLayerNodeID)
                except Exception as ex:
                    ExceptionProcessor(self.logger).logException(ex)
                    self.logger.error("abandonNodeID:{0}".format(abandonNodeID))
                    raise ValueError("can't compute path")
                path = self._modifyPathStage(path, stageNum)
                self.logger.debug(
                    "segPath:{0} layerNodeID:{1} path:{2}".format(
                        segPath, layerNodeID, path))
                pathID = self._assignPathID()
                self._addByPassPath2Set(
                    (
                        ("failureLayerNodeID", abandonLayerNodeID),
                        ("repairMethod", "fast-reroute"),
                        ("repairLayerSwitchID", (stageNum, startLayerNodeID[1])),
                        ("mergeLayerSwitchID", (stageNum, endLayerNodeID[1])),
                        ("newPathID", pathID)
                    ),
                    path)
                # For small topology,
                # it's better not allocate resource for byPass path.
                # Otherwise for some topolgoy it can't find a feasible solution
                # self._allocateResource(path)

        elif self.failureType == "link":
            if len(segPath) < 4:
                return None

            for layerNodeID in segPath[1:-2]:
                index = segPath.index(layerNodeID)
                nextIndex = index + 1

                stageNum = segPath[index][0]
                startLayerNodeID = (0, segPath[index][1])
                endLayerNodeID = (0, segPath[nextIndex][1])
                abandonLinkID = (startLayerNodeID[1], endLayerNodeID[1])
                abandonLayerLinkID = (startLayerNodeID, endLayerNodeID)

                if self._hasBackupPath(abandonLayerLinkID,
                            startLayerNodeID, endLayerNodeID):
                    continue

                mlg = MultiLayerGraph()
                mlg.loadInstance4dibAndRequest(self._dib, self.request,
                    WEIGHT_TYPE_CONST)
                    # WEIGHT_TYPE_0100_UNIFORAM_MODEL)
                mlg.addAbandonLinkIDs([abandonLinkID])
                graph = mlg.genOneLayer(0)
                try:
                    path = nx.dijkstra_path(graph, startLayerNodeID,
                        endLayerNodeID)
                except Exception as ex:
                    ExceptionProcessor(self.logger).logException(ex)
                    self.logger.error("abandonLinkID:{0}".format(abandonLinkID))
                    raise ValueError("can't compute path")
                path = self._modifyPathStage(path, stageNum)
                self.logger.debug(
                    "segPath:{0} layerNodeID:{1} path:{2}".format(
                        segPath, layerNodeID, path))
                pathID = self._assignPathID()
                self._addByPassPath2Set(
                    (
                        ("failureLayerLinkID", abandonLayerLinkID),
                        ("repairMethod", "fast-reroute"),
                        ("repairLayerSwitchID", (stageNum,
                            startLayerNodeID[1])),
                        ("mergeLayerSwitchID", (stageNum,
                            endLayerNodeID[1])),
                        ("newPathID", pathID)
                    ),
                    path)
                # For small topology,
                # it's better not allocate resource for byPass path.
                # Otherwise for some topolgoy it can't find a feasible solution
                # self._allocateResource(path)

        else:
            raise ValueError(
                "unknown faiulre type: {0}".format(self.failureType))

    def _modifyPathStage(self, path, stageNum):
        modifiedPath = []
        for layerNodeID in path:
            modifiedPath.append((stageNum, layerNodeID[1]))
        return [modifiedPath]

    def _addByPassPath2Set(self, key, path):
        self.backupForwardingPath[key] = path

    def _hasBackupPath(self, failureElementID, repairSwtichID, mergeSwitchID):
        for key in self.backupForwardingPath.keys():
            if (key[0][1] == failureElementID
                    and key[2][1] == repairSwtichID
                    and key[3][1] == mergeSwitchID):
                return True
        else:
            return False
