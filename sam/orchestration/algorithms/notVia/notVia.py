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
    def __init__(self, dib, requestList, requestForwardingPathSet):
        self._dib = dib
        self.requestList = requestList
        self.requestForwardingPathSet = requestForwardingPathSet

        logConfigur = LoggerConfigurator(__name__, './log',
            'NotVia.log', level='warning')
        self.logger = logConfigur.getLogger()

    def mapSFCI(self):
        self.logger.info("notVia mapSFCI")
        self.notVia()
        return self.requestForwardingPathSet

    def notVia(self):
        for rIndex in self.requestForwardingPathSet.keys():
            self.request = self.requestList[rIndex]
            sfc = self.request.attributes['sfc']
            self.zoneName = sfc.attributes['zone']
            self._initPathIDAssigner()
            self.primaryForwardingPath = self.requestForwardingPathSet[rIndex].primaryForwardingPath[1]
            self.backupForwardingPath = self.requestForwardingPathSet[rIndex].backupForwardingPath[1]
            for segPath in self.primaryForwardingPath:
                self._calByPassPaths4SegPath(segPath)

    def _initPathIDAssigner(self):
        self.pathID = 0

    def _assignPathID(self):
        self.pathID = self.pathID + 1
        return self.pathID

    def _calByPassPaths4SegPath(self, segPath):
        if len(segPath) < 5:
            return None

        for node in segPath[2:-2]:
            index = segPath.index(node)
            preIndex = index - 1
            nextIndex = index + 1

            stageNum = segPath[preIndex][0]
            startNode = (0, segPath[preIndex][1])
            endNode = (0, segPath[nextIndex][1])
            abandonNodeID = node[1]

            mlg = MultiLayerGraph()
            mlg.loadInstance4dibAndRequest(self._dib, self.request,
                WEIGHT_TYPE_CONST)
            mlg.addAbandonNodeIDs([abandonNodeID])
            graph = mlg.genOneLayer(0)
            path = nx.dijkstra_path(graph, startNode, endNode)
            path = self._modifyPathStage(path, stageNum)
            self.logger.debug("segPath:{0} node:{1} path:{2}".format(
                segPath, node, path))
            pathID = self._assignPathID()
            self._addByPassPath2Set((node, pathID), path)
            self._allocateResource(path)

    def _modifyPathStage(self, path, stageNum):
        modifiedPath = []
        for node in path:
            modifiedPath.append((stageNum, node[1]))
        return [modifiedPath]

    def _addByPassPath2Set(self, key, path):
        self.backupForwardingPath[key] = path
