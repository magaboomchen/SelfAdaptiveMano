#!/usr/bin/python
# -*- coding: UTF-8 -*-

import copy
import time
import math

import networkx as nx
from networkx.algorithms.link_prediction import jaccard_coefficient
from networkx.exception import NetworkXNoPath, NodeNotFound, NetworkXError

from sam.base.path import *
from sam.base.server import *
from sam.base.messageAgent import *
from sam.base.socketConverter import *
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.orchestration.algorithms.base.multiLayerGraph import *
from sam.orchestration.algorithms.base.performanceModel import *
from sam.orchestration.algorithms.base.mappingAlgorithmBase import *
from sam.orchestration.algorithms.base.pathServerFiller import *


class NetPack(MappingAlgorithmBase, PathServerFiller):
    def __init__(self, dib, topoType="fat-tree"):
        # self._dib = copy.deepcopy(dib)
        self._dib = dib
        self.topoType = topoType
        self.pM = PerformanceModel()

        self.podNum = None
        self.minPodIdx = None
        self.maxPodIdx = None

        logConfigur = LoggerConfigurator(__name__,
            './log', 'NetPack.log', level='info')
        self.logger = logConfigur.getLogger()

    # def updateServerSets(self, podNum, minPodIdx, maxPodIdx):
    #     self.podNum = podNum
    #     self.minPodIdx = minPodIdx
    #     self.maxPodIdx = maxPodIdx
    #     self.serverSets = self.getAllServerSets()

    def mapSFCI(self, requestList, podNum, minPodIdx, maxPodIdx):
        # self.logger.debug("self._dib server: {0}".format(self._dib))

        self.logger.info("NetPack mapSFCI")
        initStartTime = time.time()
        self._init(requestList, podNum, minPodIdx, maxPodIdx)
        initEndTime = time.time()
        self.logger.warning("init time is {0}".format(initEndTime - initStartTime))
        self._mapAllPrimaryPaths()
        return {"forwardingPathSetsDict": self.forwardingPathSetsDict,
                "requestOrchestrationInfo": self.requestOrchestrationInfo,
                "totalComputationTime":self.totalComputationTime}

    def _init(self, requestList, podNum, minPodIdx, maxPodIdx):
        self.requestList = requestList
        self.zoneName = self.requestList[0].attributes['zone']
        self.requestList = requestList
        if podNum != self.podNum \
            or minPodIdx != self.minPodIdx \
                or maxPodIdx != self.maxPodIdx:
            self.podNum = podNum
            self.minPodIdx = minPodIdx
            self.maxPodIdx = maxPodIdx
            self.logger.warning("update serverSets!")
            self.serverSets = self.getAllServerSets()

        self.max_attempts = 1
        if podNum == None:
            raise ValueError("NetPack needs pod number! It can only be used in DCN.")
        if  minPodIdx == None or maxPodIdx == None:
            raise ValueError("NetPack needs minPodIdx or maxPodIdx.")
        self._genRequestIngAndEg()

        # switches = self._dib.getSwitchesByZone(self.zoneName)
        # self.logger.debug("switch number: {0}".format(len(switches)))
        # for switchID in switches:
        #    self.logger.debug("switchID:{0}".format(switchID))
        # exit(1)

    def _genRequestIngAndEg(self):
        self.requestIngSwitchID = {}
        self.requestEgSwitchID = {}
        for rIndex in range(len(self.requestList)):
            # assign ing/eg switch in random style
            # ingSwitchID = random.randint(self.minPodIdx, self.maxPodIdx-1)
            # egSwitchID = random.randint(self.minPodIdx, self.maxPodIdx-1)
            ingSwitchID = self._randomSelectACoreSwitchInSubZone()
            egSwitchID = self._randomSelectACoreSwitchInSubZone()
            self.requestIngSwitchID[rIndex] = ingSwitchID
            self.requestEgSwitchID[rIndex] = egSwitchID
        # self.logger.debug("self.requestIngSwitchID:{0}, self.requestEgSwitchID:{1}".format(
        #     self.requestIngSwitchID, self.requestEgSwitchID))

    def _mapAllPrimaryPaths(self):
        self.forwardingPathSetsDict = {}
        self.primaryPathDict = {}
        # construct serversets
        preTime = time.time()
        serverSets = self.serverSets
        preEndTime = time.time()
        self.logger.warning("total pre time:{0}".format(preEndTime-preTime))
        # for serverSet in serverSets:
        #     for servers in serverSet:
        #         for server in servers:
        #             self.logger.debug(server.getServerID())
        self.requestOrchestrationInfo = {}   # "accept": true/false; "computation time": 1
        self.totalComputationTime = None
        constructStartTime = time.time()
        self.G = self.constructGraph()
        constructEndTime = time.time()
        self.logger.warning("construct graph time {0}".format(constructEndTime - constructStartTime))
        self.logger.info("_mapAllPrimaryPaths")
        totalStartTime = time.time()
        for rIndex in range(len(self.requestList)):
            request = self.requestList[rIndex]
            startTime = time.time()
            for serverSet in serverSets:
                path, acceptFlag = self._mapPrimaryPath(rIndex, request, serverSet)
                if acceptFlag == True:
                    break
            endTime = time.time()
            computationTime = endTime-startTime
            self.logger.info("computationTime:{0}".format(computationTime))
            self.requestOrchestrationInfo[rIndex] = {
                "accept": acceptFlag,
                "computationTime": computationTime
            }
            mappingType = MAPPING_TYPE_NETPACK
            self.forwardingPathSetsDict[rIndex] = ForwardingPathSet(
                {1:path}, mappingType, {1:{}})
        totalEndTime = time.time()
        self.logger.warning("total computation time:{0}".format(totalEndTime-totalStartTime))
        self.totalComputationTime = totalEndTime-totalStartTime

    def _mapPrimaryPath(self, rIndex, request, serverSet):
        # self.logger.info("map primary path for rIndex {0}".format(rIndex))
        sfc = request.attributes['sfc']
        c = sfc.getSFCLength()
        trafficDemand = sfc.getSFCTrafficDemand()
        path = None
        acceptFlag = False
        for repeat in range(self.max_attempts):
            # self.logger.info("rIndex {0} has repeat {1} times.".format(rIndex, repeat))
            # t1 = time.time()
            random.shuffle(serverSet)
            # t2 = time.time()
            # self.logger.info("shuffle time: {0}".format(t2-t1))
            for serversList in serverSet:
                # serverSet is a list
                # self.logger.info("Type of serversList is {0}".format(type(serversList)))
                failed = False
                lastServer = None
                vnf2SwitchID = [None for idx in range(c)]
                for nfIdx in range(c):
                    vnfType = sfc.vNFTypeSequence[nfIdx]
                    resourceDemand = self.pM.getExpectedServerResource(vnfType, trafficDemand)  # expectedCores, expectedMemory, expectedBandwidth
                    if lastServer == None \
                            or self._dib.hasEnoughServerResources(lastServer.getServerID(),
                                                            resourceDemand, self.zoneName):
                        validServerList = self.selectValidServerList(serversList, resourceDemand)
                        if validServerList == []:
                            failed = True
                            # if len(serversList) != 1:
                            #     self.logger.info("validServerList is empty!")
                            # restore all vnf to server resources
                            for idx,serverID in enumerate(vnf2SwitchID):
                                if serverID != None:
                                    tmpVNFType = sfc.vNFTypeSequence[idx]
                                    tmpResourceDemand = self.pM.getExpectedServerResource(tmpVNFType, trafficDemand)
                                    self._dib.releaseServerResources(serverID,
                                                            tmpResourceDemand[0], tmpResourceDemand[1],
                                                            tmpResourceDemand[2], self.zoneName)
                            break
                        else:
                            lastServer = random.choice(validServerList)
                    self._dib.reserveServerResources(lastServer.getServerID(),
                                                        resourceDemand[0], resourceDemand[1],
                                                        resourceDemand[2], self.zoneName)
                    vnf2SwitchID[nfIdx] = self._dib.getConnectedSwitch(lastServer.getServerID(), self.zoneName).switchID
                if not failed:
                    path = self.allocatePaths(rIndex, vnf2SwitchID, trafficDemand)
                    if path != None:
                        acceptFlag = True
                        return path, acceptFlag
                    else:
                        pass
                        # self.logger.info("Allocate path failed!")
        return path, acceptFlag

    def allocatePaths(self, rIndex, vnf2SwitchID, trafficDemand):
        forwardingPath = []
        ingSwitchID = self.requestIngSwitchID[rIndex]
        egSwitchID = self.requestEgSwitchID[rIndex]
        srcTerminalSwitchIDList = vnf2SwitchID
        srcTerminalSwitchIDList.insert(0, ingSwitchID)
        srcTerminalSwitchIDList.append(egSwitchID)
        self.logger.info("srcTerminalSwitchIDList: {0}".format(srcTerminalSwitchIDList))
        bandwidthReservationRecordList = []
        for idx in range(len(srcTerminalSwitchIDList)-1):
            paths = []
            u = srcTerminalSwitchIDList[idx]
            v = srcTerminalSwitchIDList[idx+1]
            if u == v:
                segPath = [u,v]
                # self.logger.info("segPath: {0}".format(segPath))
                paths.append(segPath)
                continue
            bandwidth = trafficDemand
            while bandwidth > 1 * 0.001 * 0.001 * 0.001:
                try:
                    # segPath = nx.shortest_path(self.G, u, v)
                    segPath = nx.bidirectional_shortest_path(self.G, u, v)
                    # self.logger.info("segPath: {0}".format(segPath))
                except NodeNotFound:
                    self.logger.error("NodeNotFound, u:{0}, v:{1}".format(u,v))
                    self._releaseBWFromRecordList(bandwidthReservationRecordList)
                    return None
                except NetworkXNoPath:
                    self.logger.error("no path")
                    self._releaseBWFromRecordList(bandwidthReservationRecordList)
                    return None
                except Exception as ex:
                    ExceptionProcessor(self.logger).logException(ex)
                    self.logger.error("exception")
                    self._releaseBWFromRecordList(bandwidthReservationRecordList)
                    return None
                minBW = bandwidth
                for nodeIdx in range(len(segPath)-1):
                    edge = (segPath[nodeIdx], segPath[nodeIdx+1])
                    resBW = self._dib.getLinkResidualResource(edge[0], edge[1], self.zoneName)
                    minBW = min(minBW, resBW)
                bandwidth -= minBW
                for nodeIdx in range(len(segPath)-1):
                    edge = (segPath[nodeIdx], segPath[nodeIdx+1])
                    self._dib.reserveLinkResource(edge[0], edge[1], minBW, self.zoneName)
                    bandwidthReservationRecordList.append((edge[0], edge[1], minBW))
                    if self._dib.getLinkReservedResource(edge[0], edge[1], self.zoneName) <= 1 * 0.001 * 0.001 * 0.001:
                        try:
                            self.logger.info("remove edge {0} -> {1}".format(edge[0], edge[1]))
                            self.G.remove_edge(edge[0], edge[1])
                        except NetworkXError:
                            pass
                            self.logger.error("remove link with 0 bandwidth failed!")
                paths.append(segPath)
            forwardingPath.append(paths)
        return forwardingPath

    def _releaseBWFromRecordList(self, bandwidthReservationRecordList):
        for record in bandwidthReservationRecordList:
            self._dib.reserveLinkResource(record[0], record[1], record[2], self.zoneName)

    def constructGraph(self):
        G = nx.DiGraph()
        edgeList = []
        linksInfoDict = self._dib.getLinksByZone(self.zoneName)
        for linkInfoDict in linksInfoDict.itervalues():
            link = linkInfoDict['link']
            if (self._dib.isServerID(link.srcID) 
                    or self._dib.isServerID(link.dstID)):
                continue
            if self.isSwitchInSubTopologyZone(link.srcID) and self.isSwitchInSubTopologyZone(link.dstID):
                edgeList.append((link.srcID, link.dstID))
        G.add_edges_from(edgeList)
        return G

    def isSwitchInSubTopologyZone(self, switchID):
        if self.topotype == "fat-tree":
            coreSwitchNum = math.pow(self.podNum/2, 2)
            aggSwitchNum = self.podNum * self.podNum / 2
            coreSwitchPerPod = math.floor(coreSwitchNum/self.podNum)
            # get core switch range
            minCoreSwitchIdx = self.minPodIdx * coreSwitchPerPod
            maxCoreSwitchIdx = minCoreSwitchIdx + coreSwitchPerPod * (self.maxPodIdx - self.minPodIdx + 1) - 1
            # get agg switch range
            minAggSwitchIdx = coreSwitchNum + self.minPodIdx * self.podNum / 2
            maxAggSwitchIdx = minAggSwitchIdx + self.podNum / 2 * (self.maxPodIdx - self.minPodIdx + 1) - 1
            # get tor switch range
            minTorSwitchIdx = coreSwitchNum + aggSwitchNum + self.minPodIdx * self.podNum / 2
            maxTorSwitchIdx = minTorSwitchIdx + self.podNum / 2 * (self.maxPodIdx - self.minPodIdx + 1) - 1
            # self.logger.info("{0},{1},{2},{3},{4},{5}".format(
            #         minCoreSwitchIdx, maxCoreSwitchIdx,
            #         minAggSwitchIdx, maxAggSwitchIdx,
            #         minTorSwitchIdx, maxTorSwitchIdx
            #     )
            # )

            if (switchID >= minCoreSwitchIdx and switchID <= maxCoreSwitchIdx) \
                    or (switchID >= minAggSwitchIdx and switchID <= maxAggSwitchIdx) \
                    or (switchID >= minTorSwitchIdx and switchID <= maxTorSwitchIdx):
                return True
            else:
                return False

    def selectValidServerList(self, serversList, resourceDemand):
        validServerList = []
        for server in serversList:
            if self._dib.hasEnoughServerResources(server.getServerID(),
                                            resourceDemand, self.zoneName):
                validServerList.append(server)
        return validServerList

    def getAllServerSets(self):
        if self.topoType == "fat-tree":
            coreSwitchNum = pow(self.podNum/2,2)
            aggrSwitchNum = self.podNum/2*self.podNum
            torSwitchNum = self.podNum/2*self.podNum
            torSwitchStartIdx = coreSwitchNum + aggrSwitchNum
            torSwitchEndIdx = torSwitchStartIdx + torSwitchNum - 1
            torPerPod = self.podNum/2
            # construct single serverSet
            singleServerSet = []
            for switchID in range(torSwitchStartIdx, torSwitchEndIdx+1):
                if self.isTorSwitchInSubZone(switchID):
                    rackServersList = self._dib.getConnectedServers(switchID, self.zoneName)
                    for server in rackServersList:
                        singleServerSet.append([server])
            # construct racks serverSet
            rackServerSet = []
            for switchID in range(torSwitchStartIdx, torSwitchEndIdx+1):
                if self.isTorSwitchInSubZone(switchID):
                    rackServersList = self._dib.getConnectedServers(switchID, self.zoneName)
                    rackServerSet.append(rackServersList)
            # construct pod serverSet
            podServerSet = []
            for podIdx in range(0, self.podNum):
                podServerList = []
                for switchID in range(torSwitchStartIdx+torPerPod*podIdx, torSwitchStartIdx+torPerPod*podIdx+torPerPod):
                    if self.isTorSwitchInSubZone(switchID):
                        rackServersList = self._dib.getConnectedServers(switchID, self.zoneName)
                        podServerList.extend(rackServersList)
                podServerSet.append(podServerList)
            return [singleServerSet, rackServerSet, podServerSet]
        elif self.topoType == "testbed_sw1":
            # construct single serverSet
            singleServerSet = []
            switchID = 1
            rackServersList = self._dib.getConnectedServers(switchID, self.zoneName)
            for server in rackServersList:
                singleServerSet.append([server])
            # construct racks serverSet
            rackServerSet = []
            switchID = 1
            rackServersList = self._dib.getConnectedServers(switchID, self.zoneName)
            rackServerSet.append(rackServersList)
            # construct pod serverSet
            podServerSet = []
            for podIdx in range(0, self.podNum):
                podServerList = []
                switchID = 1
                rackServersList = self._dib.getConnectedServers(switchID, self.zoneName)
                podServerList.extend(rackServersList)
                podServerSet.append(podServerList)
            return [singleServerSet, rackServerSet, podServerSet]
        else:
            raise ValueError("Unimplementation of unknown topotype: {0}".format(self.topotype))

    def isTorSwitchInSubZone(self, switchID):
        coreSwitchNum = pow(self.podNum/2,2)
        aggrSwitchNum = self.podNum/2*self.podNum
        torSwitchNum = self.podNum/2*self.podNum
        torSwitchStartIdx = coreSwitchNum + aggrSwitchNum
        torSwitchEndIdx = torSwitchStartIdx + torSwitchNum - 1
        torPerPod = self.podNum/2

        subZoneTorSwitchStartIdx = torSwitchStartIdx + self.minPodIdx * torPerPod
        subZoneTorSwitchEndIdx = subZoneTorSwitchStartIdx + (self.maxPodIdx - self.minPodIdx + 1) * torPerPod - 1

        if switchID >= subZoneTorSwitchStartIdx and switchID <= subZoneTorSwitchEndIdx:
            return True
        else:
            return False

    def _randomSelectACoreSwitchInSubZone(self):
        if self.topoType == "fat-tree":
            coreSwitchNum = math.pow(self.podNum/2, 2)
            coreSwitchPerPod = math.floor(coreSwitchNum/self.podNum)
            # get core switch range
            minCoreSwitchIdx = self.minPodIdx * coreSwitchPerPod
            maxCoreSwitchIdx = minCoreSwitchIdx + coreSwitchPerPod * (self.maxPodIdx - self.minPodIdx + 1) - 1
            coreSwitchID = random.randint(minCoreSwitchIdx, maxCoreSwitchIdx)
        elif self.topoType == "testbed_sw1":
            coreSwitchID = 1
        else:
            raise ValueError("Unimplementation topo type {0}".format(self.topoType))
        return coreSwitchID
