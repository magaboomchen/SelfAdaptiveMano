#!/usr/bin/python
# -*- coding: UTF-8 -*-

import copy
from typing import List

from sam.base.path import DIRECTION0_PATHID_OFFSET, DIRECTION1_PATHID_OFFSET, \
                            MAPPING_TYPE_MMLPSFC, ForwardingPathSet
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.request import Request
from sam.base.sfc import SFC
from sam.measurement.dcnInfoBaseMaintainer import DCNInfoBaseMaintainer
from sam.orchestration.algorithms.base.multiLayerGraph import MultiLayerGraph, \
    WEIGHT_TYPE_DELAY_MODEL
from sam.orchestration.algorithms.base.performanceModel import PerformanceModel
from sam.orchestration.algorithms.base.mappingAlgorithmBase import MappingAlgorithmBase
from sam.orchestration.algorithms.base.pathServerFiller import PathServerFiller
from sam.orchestration.oConfig import ENABLE_INGRESS_EGRESS_GENERATION, \
                                        ENABLE_PREFERRED_DEVICE_SELECTION


class MMLPSFC(MappingAlgorithmBase, PathServerFiller):
    def __init__(self, dib,        # type: DCNInfoBaseMaintainer
                    requestList    # type: List[Request]
                ):
        super(MMLPSFC, self).__init__()
        self._dib = copy.deepcopy(dib)
        self._initDib = copy.deepcopy(dib)
        self.requestList = requestList
        self.enablePreferredDeviceSelection = ENABLE_PREFERRED_DEVICE_SELECTION
        self.pM = PerformanceModel()

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
        if ENABLE_INGRESS_EGRESS_GENERATION:
            self._genRequestIngAndEg()
        else:
            self._updateRequestIngEgSwitchID()

    def _mapAllPrimaryPaths(self):
        self.forwardingPathSetsDict = {}
        self.primaryPathDict = {}
        for rIndex in range(len(self.requestList)):
            try:
                self.request = self.requestList[rIndex] # type: Request
                sfc = self.request.attributes['sfc']    # type: SFC
                c = sfc.getSFCLength()

                capacityAwareFlag = True
                while True:
                    try:
                        mlg = MultiLayerGraph(self.enablePreferredDeviceSelection)
                        mlg.loadInstance4dibAndRequest(self._dib, 
                            self.request, WEIGHT_TYPE_DELAY_MODEL)
                        mlg.trans2MLG(capacityAwareFlag)

                        ingSwitchID = self.requestIngSwitchID[rIndex]
                        egSwitchID = self.requestEgSwitchID[rIndex]

                        path = mlg.getPath(0, ingSwitchID, c, egSwitchID)
                        path = self._selectNPoPNodeAndServers(path, rIndex)
                        self.logger.debug("path:{0}".format(path))
                        break
                    except Exception as ex:
                        ExceptionProcessor(self.logger).logException(ex)
                        self.logger.warning(
                            "Can't find valid primary path for"
                            "request {0} under resource constraint".format(rIndex))
                        if capacityAwareFlag == True:
                            capacityAwareFlag = False
                        else:
                            raise ValueError(
                                "Can't find valid primary path for"
                                "request {0} even without resource capacity"
                                "constraint".format(rIndex))

                primaryPathDictCopy = copy.deepcopy(self.primaryPathDict)
                primaryPathDictCopy[rIndex] = path
                rPath = self.reverseForwardingPath(path)
                if self._isPathsMeetLatencySLA(self._initDib, primaryPathDictCopy,
                                                self.requestList):
                    self.primaryPathDict[rIndex] = path
                    self._allocateResource(path)
                    self._allocateResource(rPath)
                else:
                    raise ValueError(
                        "Can't find valid primary path for request {0}".format(
                            rIndex))

                mappingType = MAPPING_TYPE_MMLPSFC
                directionsNum = len(sfc.directions)
                if directionsNum == 1:
                    fPS = ForwardingPathSet({DIRECTION0_PATHID_OFFSET:path},
                                            mappingType,
                                            {DIRECTION0_PATHID_OFFSET:{},
                                            DIRECTION1_PATHID_OFFSET:{}})
                elif directionsNum == 2:
                    fPS = ForwardingPathSet({DIRECTION0_PATHID_OFFSET:path,
                                            DIRECTION1_PATHID_OFFSET:rPath},
                                            mappingType,
                                            {DIRECTION0_PATHID_OFFSET:{}})
                else:
                    raise ValueError("Unknown directions" \
                                    " number {0}".format(directionsNum))
            except Exception as ex:
                ExceptionProcessor(self.logger).logException(ex)
                fPS = None
            finally:
                self.forwardingPathSetsDict[rIndex] = fPS

    def _isPathsMeetLatencySLA(self, dib, pathDict, requestList):
        for rIndex in pathDict.keys():
            request = requestList[rIndex]
            sfc = self.getSFC4Request(request)
            latencySLA = sfc.getSFCLatencyBound()
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
            (layerNum, nodeID) = segPath[-1]
            if self._dib.isServerID(nodeID):
                vnfType = vnfSeq[segIndex]
                vnfLatency = pM.getLatencyOfVNF(vnfType, trafficDemand)
            elif self._dib.isSwitchID(nodeID):
                vnfLatency = pM.getSwitchLatency()
            else:
                raise ValueError("Unknown node type of nodeID {0}".format(nodeID))
            e2eLatency = e2eLatency + vnfLatency

        return e2eLatency
