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

    def _getSDC(self, request):
        sfc = self.getSFC4Request(request)
        vnfSeqList = sfc.vNFTypeSequence
        ingSwitchID = self.getIngSwitchID4Request(request)
        egSwitchID = self.getEgSwitchID4Request(request)
        sdc = (ingSwitchID, egSwitchID, self.vnfSeqList2Str(vnfSeqList))
        return sdc

    def _genPath4LinkDict(self, linkDict):
        pathList = []
        for vnfIndex in sorted(linkDict.keys()):
            firstSeg = self._findPrevForwardPath(linkDict[vnfIndex])[:-1]
            secondSeg = self._findForwardPath(linkDict[vnfIndex])
            path = firstSeg + secondSeg
            path = self._transPath2ForwardingPath(vnfIndex, path)
            pathList.append(path)
        return pathList

    def _findForwardPath(self, linkList):
        currentSwitchID = linkList[0][0]
        path = [currentSwitchID]
        while True:
            # find nextSwitchID
            for link in linkList:
                if link[0] == currentSwitchID:
                    nextSwitchID = link[1]
                    break
            else:
                nextSwitchID = None

            if nextSwitchID != None:
                path.append(nextSwitchID)
                currentSwitchID = nextSwitchID
            else:
                break
        return path

    def _findPrevForwardPath(self, linkList):
        currentSwitchID = linkList[0][0]
        path = [currentSwitchID]
        while True:
            # find prevSwitchID
            for link in linkList:
                if link[1] == currentSwitchID:
                    preSwitchID = link[0]
                    break
            else:
                preSwitchID = None

            if preSwitchID != None:
                path.insert(0, preSwitchID)
                currentSwitchID = preSwitchID
            else:
                break
        return path

    def _transPath2ForwardingPath(self, vnfIndex, path):
        forwardingPath = []
        for switchID in path:
            forwardingPath.append((vnfIndex, switchID))
        return forwardingPath

    def _insertMissingLayer(self, path, nPopDict):
        newPath = []
        for vnfIndex in sorted(nPopDict.keys()):
            if self._hasThisLayerInPath(vnfIndex, path):
                newPath.extend( self._getThisLayerInPath(vnfIndex, path) )
            else:
                newPath.extend( [(vnfIndex, nPopDict[vnfIndex])] )
        return newPath

    def _hasThisLayerInPath(self, vnfIndex, path):
        for segPath in path:
            layerNum = segPath[0][0]
            if vnfIndex == layerNum:
                return True
        else:
            return False

    def _getThisLayerInPath(self, vnfIndex, path):
        for segPath in path:
            layerNum = segPath[0][0]
            if vnfIndex == layerNum:
                return segPath
        else:
            raise ValueError("Can't find this layer in path.")

    def _genRequestIngAndEg(self):
        self.requestIngSwitchID = {}
        self.requestEgSwitchID = {}
        for rIndex in range(len(self.requestList)):
            request = self.requestList[rIndex]
            sfc = request.attributes['sfc']
            ingress = sfc.directions[0]['ingress']
            egress = sfc.directions[0]['egress']
            ingSwitch = self._dib.getConnectedSwitch(ingress.getServerID(),
                self.zoneName)
            ingSwitchID = ingSwitch.switchID
            egSwitch = self._dib.getConnectedSwitch(egress.getServerID(),
                self.zoneName)
            egSwitchID = egSwitch.switchID
            # self.logger.debug("ingSwitchID:{0}, egSwitchID:{1}".format(
            #     ingSwitchID,egSwitchID))
            self.requestIngSwitchID[rIndex] = ingSwitchID
            self.requestEgSwitchID[rIndex] = egSwitchID
        # self.logger.debug("self.requestIngSwitchID:{0}".format(
        #     self.requestIngSwitchID))

    def _updateResource4NFVCGDPInitPath(self, path):
        self._allocateSwitchResource(path)
        self._allocateLinkResource(path)

    def _allocateResource(self, path):
        # input:
        # [[(0, 10024), (0, 15), (0, 6), (0, 0), (0, 4), (0, 13), (0, 10002)],
        #  [(1, 10002), (1, 13), (1, 5), (1, 2), (1, 9), (1, 16), (1, 10025)]]
        self._allocateServerResource(path)
        self._allocateSwitchResource(path)
        self._allocateLinkResource(path)

    def _allocateServerResource(self, path):
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

    def _allocateSwitchResource(self, path):
        for segPath in path:
            for node in segPath:
                nodeID = node[1]
                if self._dib.isSwitchID(nodeID):
                    self._dib.reserveSwitchResource(
                        nodeID, 1, self.zoneName)

    # def _isSwitchID(self, nodeID):
    #     switches = self._dib.getSwitchesInAllZone()
    #     for switchesInAZoneDict in switches.values():
    #         if nodeID in switchesInAZoneDict.keys():
    #             return True
    #     else:
    #         return False

    # def _isServerID(self, nodeID):
    #     servers = self._dib.getServersInAllZone()
    #     for serversInAZoneDict in servers.values():
    #         if nodeID in serversInAZoneDict.keys():
    #             return True
    #     else:
    #         return False

    def _allocateLinkResource(self, path):
        sfc = self.request.attributes['sfc']
        trafficDemand = sfc.getSFCTrafficDemand()
        for segPath in path:
            for index in range(len(segPath)-1):
                currentNodeID = segPath[index][1]
                nextNodeID = segPath[index+1][1]
                if (self._dib.isSwitchID(currentNodeID) 
                        and self._dib.isSwitchID(nextNodeID)):
                    self._dib.reserveLinkResource(
                        currentNodeID, nextNodeID, 
                        trafficDemand, self.zoneName)
