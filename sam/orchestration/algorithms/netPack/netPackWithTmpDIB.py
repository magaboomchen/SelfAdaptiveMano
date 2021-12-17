#!/usr/bin/python
# -*- coding: UTF-8 -*-

import copy
import time
import networkx as nx
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
    def __init__(self, dib, requestList, podNum, minPodIdx, maxPodIdx):
        self._dib = copy.deepcopy(dib)
        self._dib = dib
        # self._initDib = copy.deepcopy(dib)
        self.requestList = requestList
        self.topotype = "fat-tree"
        self.podNum = podNum
        self.minPodIdx = minPodIdx
        self.maxPodIdx = maxPodIdx
        self.max_attempts = 10
        if podNum == None:
            raise ValueError("NetPack needs pod number! It can only be used in DCN.")
        if  minPodIdx == None or maxPodIdx == None:
            raise ValueError("NetPack needs minPodIdx or maxPodIdx.")
        self.pM = PerformanceModel()

        logConfigur = LoggerConfigurator(__name__,
            './log', 'NetPack.log', level='debug')
        self.logger = logConfigur.getLogger()

    def mapSFCI(self):
        self.logger.info("NetPack mapSFCI")
        self._init()
        self._mapAllPrimaryPaths()
        return {"forwardingPathSetsDict": self.forwardingPathSetsDict,
                "requestOrchestrationInfo": self.requestOrchestrationInfo}

    def _init(self):
        self.zoneName = self.requestList[0].attributes['zone']
        self._genRequestIngAndEg()

    def _genRequestIngAndEg(self):
        self.requestIngSwitchID = {}
        self.requestEgSwitchID = {}
        for rIndex in range(len(self.requestList)):
            # assign ing/eg switch in random style
            ingSwitchID = random.randint(self.minPodIdx, self.maxPodIdx-1)
            egSwitchID = random.randint(self.minPodIdx, self.maxPodIdx-1)
            self.requestIngSwitchID[rIndex] = ingSwitchID
            self.requestEgSwitchID[rIndex] = egSwitchID
        # self.logger.debug("self.requestIngSwitchID:{0}, self.requestEgSwitchID:{1}".format(
        #     self.requestIngSwitchID, self.requestEgSwitchID))

    def _mapAllPrimaryPaths(self):
        self.forwardingPathSetsDict = {}
        self.primaryPathDict = {}
        # construct serversets
        serverSets = self.getAllServerSets()
        self.requestOrchestrationInfo = {}   # "accept": true/false; "computation time": 1
        self.tmpDib = copy.deepcopy(self._dib)
        self.G = self.constructGraph()
        self.logger.info("_mapAllPrimaryPaths")
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

    def _mapPrimaryPath(self, rIndex, request, serverSet):
        self.logger.info("map primary path for rIndex {0}".format(rIndex))
        sfc = request.attributes['sfc']
        c = sfc.getSFCLength()
        trafficDemand = sfc.getSFCTrafficDemand()
        path = None
        acceptFlag = False
        for repeat in range(self.max_attempts):
            self.logger.info("rIndex {0} has repeat {1} times.".format(rIndex, repeat))
            for serversList in serverSet:
                # serverSet is a list
                # self.logger.info("Type of serversList is {0}".format(type(serversList)))

                # t1 = time.time()
                random.shuffle(serversList)
                # t2 = time.time()
                # self.logger.info("shuffle time: {0}".format(t2-t1))

                failed = False

                # t1 = time.time()
                self.tmpDib = copy.deepcopy(self._dib)
                # t2 = time.time()
                # self.logger.info("copy dib time: {0}".format(t2-t1))

                lastServer = None
                vnf2SwitchID = [None for idx in range(c)]
                for nfIdx in range(c):
                    vnfType = sfc.vNFTypeSequence[nfIdx]
                    resourceDemand = self.pM.getExpectedServerResource(vnfType, trafficDemand)  # expectedCores, expectedMemory, expectedBandwidth
                    if lastServer == None \
                            or self.tmpDib.hasEnoughServerResources(lastServer.getServerID(),
                                                            resourceDemand, self.zoneName):
                        validServerList = self.selectValidServerList(serversList, resourceDemand)
                        if validServerList == []:
                            failed = True
                            # restore
                            break
                        else:
                            lastServer = random.choice(validServerList)
                    self.tmpDib.reserveServerResources(lastServer.getServerID(),
                                                        resourceDemand[0], resourceDemand[1],
                                                        resourceDemand[2], self.zoneName)
                    vnf2SwitchID[nfIdx] = self.tmpDib.getConnectedSwitch(lastServer.getServerID(), self.zoneName).switchID
                if not failed:
                    path = self.allocatePaths(rIndex, vnf2SwitchID, trafficDemand)
                    if path != None:
                        self._dib = copy.deepcopy(self.tmpDib)
                        acceptFlag = True
                        return path, acceptFlag
                    else:
                        self.logger.info("Allocate path failed!")
        return path, acceptFlag

    def allocatePaths(self, rIndex, vnf2SwitchID, trafficDemand):
        forwardingPath = []
        ingSwitchID = self.requestIngSwitchID[rIndex]
        egSwitchID = self.requestEgSwitchID[rIndex]
        # t1 = time.time()
        srcTerminalSwitchIDList = copy.deepcopy(vnf2SwitchID)
        # t2 = time.time()
        # self.logger.info("switchID seq copy time: {0}".format(t2-t1))
        srcTerminalSwitchIDList.insert(0, ingSwitchID)
        srcTerminalSwitchIDList.append(egSwitchID)
        self.logger.info("srcTerminalSwitchIDList: {0}".format(srcTerminalSwitchIDList))
        for idx in range(len(srcTerminalSwitchIDList)-1):
            paths = []
            u = srcTerminalSwitchIDList[idx]
            v = srcTerminalSwitchIDList[idx+1]
            if u == v:
                segPath = [u,v]
                self.logger.info("segPath: {0}".format(segPath))
                paths.append(segPath)
                continue
            bandwidth = trafficDemand
            while bandwidth > 1 * 0.001 * 0.001 * 0.001:
                try:
                    segPath = nx.shortest_path(self.G, u, v)
                    self.logger.info("segPath: {0}".format(segPath))
                except NodeNotFound:
                    self.logger.error("NodeNotFound")
                    return None
                except NetworkXNoPath:
                    self.logger.error("no path")
                    return None
                except Exception as ex:
                    ExceptionProcessor(self.logger).logException(ex)
                    self.logger.error("exception")
                    return None
                minBW = bandwidth
                for nodeIdx in range(len(segPath)-1):
                    edge = (segPath[nodeIdx], segPath[nodeIdx+1])
                    resBW = self.tmpDib.getLinkResidualResource(edge[0], edge[1], self.zoneName)
                    minBW = min(minBW, resBW)
                bandwidth -= minBW
                for nodeIdx in range(len(segPath)-1):
                    edge = (segPath[nodeIdx], segPath[nodeIdx+1])
                    self.tmpDib.reserveLinkResource(edge[0], edge[1], minBW, self.zoneName)
                    if self.tmpDib.getLinkReservedResource(edge[0], edge[1], self.zoneName) <= 1 * 0.001 * 0.001 * 0.001:
                        try:
                            self.G.remove_edge(edge[0], edge[1])
                        except NetworkXError:
                            self.logger.error("remove link with 0 bandwidth failed!")
                paths.append(segPath)
            forwardingPath.append(paths)
        return forwardingPath

    def constructGraph(self):
        G = nx.DiGraph()
        edgeList = []
        linksInfoDict = self.tmpDib.getLinksByZone(self.zoneName)
        for linkInfoDict in linksInfoDict.itervalues():
            link = linkInfoDict['link']
            if (self.tmpDib.isServerID(link.srcID) 
                    or self.tmpDib.isServerID(link.dstID)):
                continue
            if self.isSwitchInSubTopologyZone(link.srcID) and self.isSwitchInSubTopologyZone(link.dstID):
                edgeList.append((link.srcID, link.dstID))
        G.add_edges_from(edgeList)
        return G

    def isSwitchInSubTopologyZone(self, switchID):
        if self.topotype == "fat-tree":
            coreSwitchNum = self.podNum
            aggSwitchNum = self.podNum * self.podNum / 2 
            # get core switch range
            minCoreSwitchIdx = self.minPodIdx
            maxCoreSwitchIdx = minCoreSwitchIdx + (self.maxPodIdx - self.minPodIdx + 1) - 1
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
            if self.tmpDib.hasEnoughServerResources(server.getServerID(),
                                            resourceDemand, self.zoneName):
                validServerList.append(server)
        return validServerList

    def getAllServerSets(self):
        if self.topotype == "fat-tree":
            coreSwitchNum = pow(self.podNum/2,2)
            aggrSwitchNum = self.podNum/2*self.podNum
            torSwitchNum = self.podNum/2*self.podNum
            torSwitchStartIdx = coreSwitchNum + aggrSwitchNum
            torSwitchEndIdx = torSwitchStartIdx + torSwitchNum - 1
            torPerPod = self.podNum/2
            # construct single serverSet
            singleServerSet = []
            for switchID in range(torSwitchStartIdx, torSwitchEndIdx+1):
                rackServersList = self._dib.getConnectedServers(switchID, self.zoneName)
                for server in rackServersList:
                    singleServerSet.append([server])
            # construct racks serverSet
            rackServerSet = []
            for switchID in range(torSwitchStartIdx, torSwitchEndIdx+1):
                rackServersList = self._dib.getConnectedServers(switchID, self.zoneName)
                rackServerSet.append(rackServersList)
            # construct pod serverSet
            podServerSet = []
            for podIdx in range(0, self.podNum):
                podServerList = []
                for switchID in range(torSwitchStartIdx+torPerPod*podIdx, torSwitchStartIdx+torPerPod*podIdx+torPerPod):
                    rackServersList = self._dib.getConnectedServers(switchID, self.zoneName)
                    podServerList.extend(rackServersList)
                podServerSet.append(podServerList)
            return [singleServerSet, rackServerSet, podServerSet]
        else:
            raise ValueError("Unimplementation of unknown topotype: {0}".format(self.topotype))