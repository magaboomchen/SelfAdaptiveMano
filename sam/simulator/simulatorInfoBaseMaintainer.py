#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
store dcn information
e.g. switch, server, link, sfc, sfci, vnfi, flow
'''
import math
import numpy as np
from typing import List

from sam.base.path import DIRECTION1_PATHID_OFFSET, DIRECTION2_PATHID_OFFSET
from sam.base.pickleIO import PickleIO
from sam.base.sfc import SFC, SFCI
from sam.measurement.dcnInfoBaseMaintainer import DCNInfoBaseMaintainer
from sam.base.link import Link
from sam.base.socketConverter import SocketConverter
from sam.base.server import Server

BG_LINK_NUM = 1000


class SimulatorInfoBaseMaintainer(DCNInfoBaseMaintainer):
    def __init__(self):
        super(SimulatorInfoBaseMaintainer, self).__init__()
        self.pIO = PickleIO()
        self.sc = SocketConverter()

        self.links = {}
        self.switches = {}
        self.servers = {}
        self.serverLinks = {}
        self.sfcs = {}
        self.sfcis = {}
        self.flows = {}
        self.bgProcesses = {}
        self.vnfis = {}
        self.podPaths = []

    def reset(self):
        self.links.clear()
        self.switches.clear()
        self.servers.clear()
        self.serverLinks.clear()
        self.sfcs.clear()
        self.sfcis.clear()
        self.flows.clear()
        self.bgProcesses.clear()
        self.vnfis.clear()
        self.podPaths = []

    def loadTopology(self, topoFilePath):
        topologyDict = self.pIO.readPickleFile(topoFilePath)
        # more details in /sam/simulator/test/readme.md

        self.links = topologyDict["links"]
        self.switches = topologyDict["switches"]
        self.servers = topologyDict["servers"]
        self.serverLinks = topologyDict["serverLinks"]
        self.sfcs = topologyDict["sfcs"]
        self.sfcis = topologyDict["sfcis"]
        self.flows = topologyDict["flows"]
        self.vnfis = topologyDict["vnfis"]
        self.bgProcesses = topologyDict["bgProcesses"]
        self.podPaths = topologyDict["podPaths"]

    def saveTopology(self, topoFilePath):
        topologyDict = {
            "links": self.links,
            "switches": self.switches,
            "servers": self.servers,
            "serverLinks": self.serverLinks,
            "sfcs": self.sfcs,
            "sfcis": self.sfcis,
            "flows": self.flows,
            "vnfis": self.vnfis,
            "bgProcesses": self.bgProcesses,
            "podPaths": self.podPaths,
        }

        self.pIO.writePickleFile(topoFilePath, topologyDict)

    def turnOffSwitch(self, switchID):
        if switchID not in self.switches:
            raise ValueError('Unknown switch.')
        self.switches[switchID]['Active'] = False
        # CLI > switch 3 down

    def turnOnSwitch(self, switchID):
        if switchID not in self.switches:
            raise ValueError('Unknown switch.')
        self.switches[switchID]['Active'] = True
        # CLI > switch 3 up

    def turnOffLink(self, srcID, dstID):
        if (srcID, dstID) not in self.links:
            raise ValueError('Unknown link.')
        self.links[(srcID, dstID)]['Active'] = False

    def turnOnLink(self, srcID, dstID):
        if (srcID, dstID) not in self.links:
            raise ValueError('Unknown link.')
        self.links[(srcID, dstID)]['Active'] = True

    def turnOnServer(self, serverID):
        if serverID not in self.servers:
            raise ValueError('Unknown server.')
        self.servers[serverID]['Active'] = True

    def turnOffServer(self, serverID):
        if serverID not in self.servers:
            raise ValueError('Unknown server.')
        self.servers[serverID]['Active'] = False

    def getSFCIFlowIdentifierDict(self, sfciID, stageIndex):
        sfci = self.sfcis[sfciID]['sfci']  # type: SFCI
        sfc = self.sfcis[sfciID]['sfc']  # type: SFC
        identifierDict = sfc.routingMorphic.getIdentifierDict()
        identifierDict['value'] = sfc.routingMorphic.encodeIdentifierForSFC(sfci.sfciID,
                                                                            sfci.vnfiSequence[stageIndex][0].vnfID)
        identifierDict['humanReadable'] = sfc.routingMorphic.value2HumanReadable(identifierDict['value'])
        return identifierDict
        # Flow Identifier is a unique id of each flow
        # E.g. IPv4 destination address of a flow is an identifier
        # Flow's IdentifierDict refer to sam/base/flow.py
        # <object routingMorphic> = <object sfc>.routingMorphic
        # identifierDict = <object routingMorphic>.getIdentifierDict()
        # identifierDict['value'] = <object routingMorphic>.encodeIdentifierForSFC(sfciID, vnfID)
        # identifierDict['humanReadable'] = <object routingMorphic>.value2HumanReadable(identifierDict['value'])
        # flow(identifierDict)

    def updateServerResource(self):
        serverProcesses = {}
        for serverID, vnfis in self.vnfis:
            serverProcesses[serverID] = [{'cpu': vnfi['cpu'](), 'mem': vnfi['mem']} for vnfi in vnfis]

        for serverID, process in self.bgProcesses:
            serverProcesses.setdefault(serverID, []).append({'cpu': process['cpu'](), 'mem': process['mem']()})

        for serverID, processes in serverProcesses:
            server = self.servers[serverID]['server']  # type: Server
            cpu = reduce(lambda x, y: x + y, [process['cpu'] for process in processes])
            distribution = server.getCoreNUMADistribution()
            utilization = [0] * len(server.getCpuUtil())
            for singleCpu in distribution:
                for core in singleCpu:
                    if cpu <= 0:
                        break
                    usage = min(cpu, 100)
                    utilization[core] = usage
                    cpu -= usage
            server.setCpuUtil(utilization)

            pageSize = server.getHugepagesSize()
            pageUsage = reduce(lambda x, y: x + y,
                               [int(math.ceil(process['mem'] * 1024 / pageSize)) for process in processes])
            server.setHugePages(server.getHugepagesTotal() - pageUsage)

    def updateLinkUtilization(self):
        for linkInfo in self.links.values():
            link = linkInfo['link']
            link.utilization = 0.0

        for sfciID, sfci in self.sfcis.items():
            directions = sfci['sfc'].directions
            primaryForwardingPath = sfci['sfci'].forwardingPathSet.primaryForwardingPath
            for direction in directions:
                dirID = direction['ID']
                if dirID == 0:
                    pathlist = primaryForwardingPath[DIRECTION1_PATHID_OFFSET]
                elif dirID == 1:
                    pathlist = primaryForwardingPath[DIRECTION2_PATHID_OFFSET]
                if len(sfci['traffics'][dirID]) == 0:
                    bw = 0
                else:
                    bw = reduce(lambda x, y: x + y,
                                [self.flows[traffic_id]['bw']() for traffic_id in sfci['traffics'][dirID]])
                for stage, path in enumerate(pathlist):
                    for hop, (_, srcID) in enumerate(path):
                        if hop != len(path) - 1:
                            dstID = path[hop + 1][1]
                            if hop == 0:  # server -> switch, switchID is server
                                link = self.serverLinks[(srcID, dstID)]['link']  # type: Link
                            elif hop == len(path) - 2:  # switch -> server
                                link = self.serverLinks[(srcID, dstID)]['link']
                            else:  # switch -> switch
                                link = self.links[(srcID, dstID)]['link']
                            link.utilization = min(100 * bw / (link.bandwidth * 1024), 100.0)

        tm = np.random.uniform(0.0, 1024.0, (384, 384))
        index = np.random.rand(384, 384)
        scale = float(BG_LINK_NUM) / (384 * 383)
        for i in range(384):
            for j in range(384):
                if i == j or index[i][j] > scale:
                    continue
                paths = self.shortestPaths(i + 896, j + 896)
                parts = len(paths)
                for path in paths:
                    for link in path:
                        link.utilization = min(100 * tm[i][j] / parts / (link.bandwidth * 1024) + link.utilization,
                                               100.0)

    def shortestPaths(self, i, j):
        # type: (int, int) -> List[List[Link]]
        pod_i = (i - 768) // 16
        pod_j = (j - 768) // 16
        paths = []
        for podPath in self.podPaths[pod_i][pod_j]:
            paths.append([self.links[(i, podPath[0])]['link']])
            for ii, src in enumerate(podPath):
                if ii != len(podPath) - 1:
                    paths[-1].append(self.links[(src, podPath[ii + 1])]['link'])
                else:
                    paths[-1].append(self.links[(src, j)]['link'])
        return paths
