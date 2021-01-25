#!/usr/bin/python
# -*- coding: UTF-8 -*-

import copy

import networkx as ax

from sam.base.path import *
from sam.base.server import *
from sam.base.messageAgent import *
from sam.base.socketConverter import *
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.orchestration.algorithms.pSFC.partialLP import *
from sam.orchestration.algorithms.pSFC.pRandomizedRoundingAlgorithm import *
from sam.orchestration.algorithms.multiLayerGraph import *
from sam.orchestration.algorithms.base.mappingAlgorithmBase import *


class NotVia(MappingAlgorithmBase):
    def __init__(self, dib, requestList, forwardingPathSetsDict):
        self._dib = dib
        self.requestList = requestList
        self.forwardingPathSetsDict = forwardingPathSetsDict
        self.failureType = "node"

        logConfigur = LoggerConfigurator(__name__, './log',
            'NotVia.log', level='warning')
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

                if self._hasBackupPath(abandonNodeID):
                    continue

                mlg = MultiLayerGraph()
                mlg.loadInstance4dibAndRequest(self._dib, self.request,
                    WEIGHT_TYPE_CONST)
                mlg.addAbandonNodeIDs([abandonNodeID])
                graph = mlg.genOneLayer(0)
                path = nx.dijkstra_path(graph, startLayerNodeID,
                    endLayerNodeID)
                path = self._modifyPathStage(path, stageNum)
                self.logger.debug(
                    "segPath:{0} layerNodeID:{1} path:{2}".format(
                        segPath, layerNodeID, path))
                pathID = self._assignPathID()
                self._addByPassPath2Set(
                    (
                        ("failureNodeID", abandonNodeID),
                        ("repairMethod", "fast-reroute"),
                        ("repairSwitchID", startLayerNodeID[1]),
                        ("mergeSwitchID", endLayerNodeID[1]),
                        ("newPathID", pathID)
                    ),
                    path)
                self._allocateResource(path)

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

                if self._hasBackupPath(abandonLinkID):
                    continue

                mlg = MultiLayerGraph()
                mlg.loadInstance4dibAndRequest(self._dib, self.request,
                    WEIGHT_TYPE_CONST)
                mlg.addAbandonLinkIDs([abandonLinkID])
                graph = mlg.genOneLayer(0)
                path = nx.dijkstra_path(graph, startLayerNodeID,
                    endLayerNodeID)
                path = self._modifyPathStage(path, stageNum)
                self.logger.debug(
                    "segPath:{0} layerNodeID:{1} path:{2}".format(
                        segPath, layerNodeID, path))
                pathID = self._assignPathID()
                self._addByPassPath2Set(
                    (
                        ("failureLinkID", abandonLinkID),
                        ("repairMethod", "fast-reroute"),
                        ("repairSwitchID", startLayerNodeID[1]),
                        ("mergeSwitchID", endLayerNodeID[1]),
                        ("newPathID", pathID)
                    ),
                    path)
                self._allocateResource(path)

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

    def _hasBackupPath(self, failureElementID):
        for key in self.backupForwardingPath.keys():
            if key[0][1] == failureElementID:
                return True
        else:
            return False
