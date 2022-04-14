#!/usr/bin/python
# -*- coding: UTF-8 -*-

import copy

from sam.serverController.serverManager.serverManager import SeverManager, SERVERID_OFFSET
from sam.orchestration.algorithms.base.performanceModel import *


class PathServerFiller(object):
    def __init__(self):
        self.abandonElementIDList = []

    def _selectNPoPNodeAndServers(self, path, rIndex, abandonElementIDList=[]):
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

        request = self.requestList[rIndex]

        dividedPath = self._dividePath(path)

        # add ingress and egress
        ingID = self._getIngressID(request)
        egID = self._getEgressID(request)
        dividedPath = self._addStartNodeIDAndEndNodeID2Path(dividedPath,
            ingID, egID)

        # select a server for each stage
        serverList = self._selectNFVI4EachStage(dividedPath, request,
            abandonElementIDList)
        dividedPath = self._addNFVI2Path(dividedPath, serverList)
        self.logger.info("ingID:{0}, egID:{1}, dividedPath:{2}".format(
                ingID, egID, dividedPath))

        return dividedPath

    def _dividePath(self, path):
        pathSegment = {}
        for node in path:
            stage = node[0]
            nodeID = node[1]
            if stage not in pathSegment.keys():
                pathSegment[stage] = []
            pathSegment[stage].append(node)

        dividedPath = []
        for stage in pathSegment.keys():
            dividedPath.append(pathSegment[stage])
        self.logger.debug("dividedPath:{0}".format(dividedPath))
        return dividedPath

    def _getIngressID(self, request):
        sfc = request.attributes['sfc']
        ingress = sfc.directions[0]['ingress']
        return ingress.getServerID()

    def _getEgressID(self, request):
        sfc = request.attributes['sfc']
        egress = sfc.directions[0]['egress']
        return egress.getServerID()

    def _addStartNodeIDAndEndNodeID2Path(self, dividedPath,
                                        startNodeID, endNodeID):
        dividedPath[0].insert(0, (0, startNodeID))
        lastLayerNum = dividedPath[-1][0][0]
        # dividedPath[-1].append((len(dividedPath)-1, endNodeID))
        dividedPath[-1].append((lastLayerNum, endNodeID))
        self.logger.debug(
            "add start and end node to dividedPath:{0}".format(
                dividedPath))
        return dividedPath

    def _addEndNodeID2Path(self, dividedPath, endNodeID):
        lastLayerNum = dividedPath[-1][0][0]
        # dividedPath[-1].append((len(dividedPath)-1, endNodeID))
        dividedPath[-1].append((lastLayerNum, endNodeID))
        self.logger.debug(
            "add end node ID {0} to dividedPath:{1}".format(
                endNodeID, dividedPath))
        return dividedPath

    def _selectNFVI4EachStage(self, dividedPath, request,
                                abandonElementIDList=[]):
        self.abandonElementIDList = abandonElementIDList
        sfc = request.attributes['sfc']
        trafficDemand = sfc.getSFCTrafficDemand()
        c = sfc.getSFCLength()
        serverList = []
        self.logger.debug(dividedPath)
        dividedPathLength = len(dividedPath)
        startIndex = c+1 - dividedPathLength
        # for index in range(startIndex, c):
        for index in range(len(dividedPath)-1):
            layerNum = dividedPath[index][0][0]
            vnfType = sfc.vNFTypeSequence[layerNum]
            switchID = dividedPath[index][-1][1]
            self.logger.debug("switchID:{0}".format(switchID))
            servers = self._dib.getConnectedNFVIs(switchID,
                self.zoneName)
            servers = self._delAbandonedServer(servers)
            # self.logger.warning("servers:{0}".format(servers))
            server = self._selectServer4ServerList(servers,
                vnfType, trafficDemand)
            serverList.append(server)
        return serverList

    def _delAbandonedServer(self, servers):
        servers = copy.deepcopy(servers)
        for server in servers:
            serverID = server.getServerID()
            if serverID in self.abandonElementIDList:
                servers.remove(server)
        return servers

    def _selectServer4ServerList(self, serverList, vnfType, trafficDemand):
        # First-fit algorithm
        for server in serverList:
            if self._hasEnoughResource(server, vnfType, trafficDemand):
                return server
        else:
            self.logger.debug("serverList:{0}".format(serverList))
            raise ValueError("No available server resource")

    def _isServerInAbandonElementsList(self, server):
        serverID = server.getServerID()
        return serverID in self.abandonElementIDList

    def _hasEnoughResource(self, server, vnfType, trafficDemand):
        pM = PerformanceModel()
        (expectedCores, expectedMemory, 
            expectedBandwidth) = pM.getExpectedServerResource(vnfType,
                trafficDemand)
        serverID = server.getServerID()
        return self._dib.hasEnoughServerResources(
            serverID, (expectedCores, expectedMemory, expectedBandwidth),
                self.zoneName)

    def _addNFVI2Path(self, dividedPath, serverList):
        # self.logger.debug("dividedPath:{0}".format(dividedPath))
        # for server in serverList:
        #     self.logger.debug("serverID:{0}".format(server.getServerID()))

        startVNFStageNum = dividedPath[0][0][0]

        for index in range(len(serverList)):
            currentIndex = index
            nextIndex = index + 1
            serverID = serverList[currentIndex].getServerID()
            dividedPath[currentIndex].append((currentIndex+startVNFStageNum,serverID))
            dividedPath[nextIndex].insert(0, (nextIndex+startVNFStageNum, serverID))
        self.logger.debug("new dividedPath:{0}".format(dividedPath))
        return dividedPath
