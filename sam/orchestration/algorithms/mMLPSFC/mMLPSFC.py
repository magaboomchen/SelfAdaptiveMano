#!/usr/bin/python
# -*- coding: UTF-8 -*-

import copy

from sam.base.path import *
from sam.base.server import *
from sam.base.messageAgent import *
from sam.base.socketConverter import *
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.orchestration.algorithms.base.multiLayerGraph import *
from sam.orchestration.algorithms.base.performanceModel import *
from sam.orchestration.algorithms.base.mappingAlgorithmBase import *
from sam.orchestration.algorithms.base.pathServerFiller import *


class MMLPSFC(MappingAlgorithmBase, PathServerFiller):
    def __init__(self, dib, requestList):
        self._dib = copy.deepcopy(dib)
        self._initDib = copy.deepcopy(dib)
        self.requestList = requestList

        logConfigur = LoggerConfigurator(__name__,
            './log', 'MMLPSFC.log', level='debug')
        self.logger = logConfigur.getLogger()

    def mapSFCI(self):
        self.logger.info("MMLPSFC mapSFCI")
        self._init()
        self._mapAllPrimaryPaths()
        return self.forwardingPathSetsDict

    def _init(self):
        self.zoneName = self.requestList[0].attributes['zone']
        self._genRequestIngAndEg()

    def _mapAllPrimaryPaths(self):
        self.forwardingPathSetsDict = {}
        self.primaryPathDict = {}
        for rIndex in range(len(self.requestList)):
            self.request = self.requestList[rIndex]
            sfc = self.request.attributes['sfc']
            c = sfc.getSFCLength()

            mlg = MultiLayerGraph()
            mlg.loadInstance4dibAndRequest(self._dib, 
                self.request, WEIGHT_TYPE_DELAY_MODEL)
            mlg.trans2MLG()

            ingSwitchID = self.requestIngSwitchID[rIndex]
            egSwitchID = self.requestEgSwitchID[rIndex]

            try:
                path = mlg.getPath(0, ingSwitchID, c, egSwitchID)
                path = self._selectNPoPNodeAndServers(path, rIndex)
                self.logger.debug("path:{0}".format(path))
            except Exception as ex:
                ExceptionProcessor(self.logger).logException(ex)
                self.logger.warning(
                    "Can't find valid primary path for request {0}".format(
                        rIndex))
                break

            primaryPathDictCopy = copy.deepcopy(self.primaryPathDict)
            primaryPathDictCopy[rIndex] = path
            if self._isPathsMeetLatencySLA(self._initDib, primaryPathDictCopy,
                                            self.requestList):
                self.primaryPathDict[rIndex] = path
                self._allocateResource(path)
            else:
                raise ValueError(
                    "Can't find valid primary path for request {0}".format(
                        rIndex))

            mappingType = MAPPING_TYPE_UFRR
            self.forwardingPathSetsDict[rIndex] = ForwardingPathSet(
                {1:path}, mappingType, {1:{}})

    def _isPathsMeetLatencySLA(self, dib, pathDict, requestList):
        for rIndex in pathDict.keys():
            request = requestList[rIndex]
            sfc = self.getSFC4Request(request)
            latencySLA = sfc.getSFCLatencyBound
            path = pathDict[rIndex]
            latency = self._getPathLatency(dib, request, path)
            # self.logger.debug("e2e latency: {0}".format(latency))
            if latency > latencySLA:
                return False
        else:
            return True

    def _getPathLatency(self, dib, request, path):
        # input: tour from ingress to egress passing through vnfis
        e2eLatency = 0

        # get links latency
        mlg = MultiLayerGraph()
        mlg.loadInstance4dibAndRequest(dib, request, WEIGHT_TYPE_DELAY_MODEL)
        for segPath in path:
            for nodeIndex in range(1, len(segPath)-2):
                (srcLayerNum, srcNodeID) = segPath[nodeIndex]
                (dstLayerNum, dstNodeID) = segPath[nodeIndex + 1]
                link = self._dib.getLink(srcNodeID, dstNodeID, self.zoneName)
                linkLatency = mlg.getLinkWeight(link)
                e2eLatency = e2eLatency + linkLatency

        # get server latency
        sfc = self.getSFC4Request(request)
        trafficDemand = sfc.getSFCTrafficDemand()
        vnfSeq = sfc.vNFTypeSequence
        pM = PerformanceModel()
        for segIndex in range(len(path)-1):
            segPath = path[segIndex]
            (layerNum, serverID) = segPath[-1]
            # if not self._isServerID(serverID):
            if not self._dib.isServerID(serverID):
                raise ValueError("Invalid serverID: {0}".format(serverID))
            vnfType = vnfSeq[segIndex]
            vnfLatency = pM.getLatencyOfVNF(vnfType, trafficDemand)
            e2eLatency = e2eLatency + vnfLatency

        return e2eLatency
