#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.serverController.serverManager.serverManager import *
from sam.orchestration.algorithms.performanceModel import *


class MappingAlgorithmBase(object):
    def __init__(self):
        pass

    def getSFC4Request(self, request):
        sfc = request.attributes['sfc']
        return sfc

    def getIngSwitchID4Request(self, request):
        sfc = request.attributes['sfc']
        ingID = sfc.directions[0]['ingress'].getServerID()
        ingSwitch = self._dib.getConnectedSwitch(ingID, self.zoneName)
        ingSwitchID = ingSwitch.switchID
        return ingSwitchID

    def getEgSwitchID4Request(self, request):
        sfc = request.attributes['sfc']
        egID = sfc.directions[0]['egress'].getServerID()
        egSwitch = self._dib.getConnectedSwitch(egID, self.zoneName)
        egSwitchID = egSwitch.switchID
        return egSwitchID

    def vnfSeqList2Str(self, vnfSeqList):
        vnfSeqStr = ''
        for vnfType in vnfSeqList:
            vnfSeqStr = vnfSeqStr + str(vnfType) + '_'
        return vnfSeqStr

    def vnfSeqStr2List(self, vnfSeqStr):
        vnfSeqList = []
        vnfSeqStrList = vnfSeqStr.strip('\n').split('_')
        for vnfType in vnfSeqStrList:
            if vnfType != '_' and vnfType != '':
                vnfSeqList.append(int(vnfType))
        return vnfSeqList

    def getvnfSeqStrLength(self, vnfSeqStr):
        return len(self.vnfSeqStr2List(vnfSeqStr))

    def _updateResource(self, path):
        # [[(0, 10024), (0, 15), (0, 6), (0, 0), (0, 4), (0, 13), (0, 10002)], [(1, 10002), (1, 13), (1, 5), (1, 2), (1, 9), (1, 16), (1, 10025)]]
        self._updateServerResource(path)
        self._updateSwitchResource(path)
        self._updateLinkResource(path)

    def _updateServerResource(self, path):
        for index in range(1, len(path)):
            serverID = path[index][0]

            sfc = self.request.attributes['sfc']
            vnfType = sfc.vNFTypeSequence[index-1]
            trafficDemand = sfc.getSFCTrafficDemand()

            pM = PerformanceModel()
            (expectedCores, expectedMemory, 
                expectedBandwidth) = pM.getExpectedServerResource(
                    vnfType, trafficDemand)
            self._dib.reserveServerResources(
                serverID, expectedCores, expectedMemory,
                expectedBandwidth, self.zoneName)

    def _updateSwitchResource(self, path):
        for segPath in path:
            for node in segPath:
                nodeID = node[1]
                if self._isSwitch(nodeID):
                    self._dib.reserveSwitchResource(
                        nodeID, 1, self.zoneName)

    def _isSwitch(self, nodeID):
        return nodeID < SERVERID_OFFSET

    def _isServer(self, nodeID):
        return nodeID >= SERVERID_OFFSET

    def _updateLinkResource(self, path):
        sfc = self.request.attributes['sfc']
        trafficDemand = sfc.getSFCTrafficDemand()
        for segPath in path:
            for index in range(1, len(segPath)-2):
                currentNodeID = segPath[index][1]
                nextNodeID = segPath[index+1][1]
                self._dib.reserveLinkResource(
                    currentNodeID, nextNodeID, trafficDemand, self.zoneName)
