#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
store dcn information
e.g. switch, server, link, sfc, sfci, vnfi, flow
'''
import math
import random

import numpy as np

from sam.base.path import DIRECTION1_PATHID_OFFSET, DIRECTION2_PATHID_OFFSET
from sam.base.pickleIO import PickleIO
from sam.base.sfc import SFC, SFCI
from sam.base.slo import SLO
from sam.measurement.dcnInfoBaseMaintainer import DCNInfoBaseMaintainer
from sam.base.link import Link
from sam.base.socketConverter import SocketConverter
from sam.base.server import Server
from sam.orchestration.algorithms.base.performanceModel import PerformanceModel

MAX_BG_BW = 1024.0 * 3
# BG_RATIO = 0.75
CHECK_CONNECTIVITY = True


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
        self.torPaths = []

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
        self.torPaths = []

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
        self.torPaths = topologyDict["torPaths"]

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
            "torPaths": self.torPaths,
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
        for serverID, vnfis in self.vnfis.items():
            serverProcesses[serverID] = [{'cpu': vnfi['cpu'](), 'mem': vnfi['mem']} for vnfi in vnfis]

        for serverID, process in self.bgProcesses.items():
            serverProcesses.setdefault(serverID, []).append({'cpu': process['cpu'](), 'mem': process['mem']()})

        for serverID, processes in serverProcesses.items():
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
        for linkInfo in self.serverLinks.values():
            link = linkInfo['link']
            link.utilization = 0.0
        for linkInfo in self.links.values():
            link = linkInfo['link']
            link.utilization = 0.0

        links = {}
        sfcis = {}
        performanceModel = PerformanceModel()

        for sfciID, sfci in self.sfcis.items():
            directions = sfci['sfc'].directions
            primaryForwardingPath = sfci['sfci'].forwardingPathSet.primaryForwardingPath
            for direction in directions:
                dirID = direction['ID']
                if dirID == 0:
                    pathlist = primaryForwardingPath[DIRECTION1_PATHID_OFFSET]
                else:
                    pathlist = primaryForwardingPath[DIRECTION2_PATHID_OFFSET]
                if len(sfci['traffics'][dirID]) == 0:
                    bw = 0
                else:
                    bw = reduce(lambda x, y: x + y,
                                [self.flows[traffic_id]['bw']() for traffic_id in sfci['traffics'][dirID]])
                sfcis.setdefault(sfciID, {})[dirID] = bw
                for stage, path in enumerate(pathlist):
                    for hop, (_, srcID) in enumerate(path):
                        if hop != len(path) - 1:
                            dstID = path[hop + 1][1]
                            if srcID == dstID:
                                continue
                            links[(srcID, dstID)] = links.setdefault((srcID, dstID), 0) + bw

        for sfciID, sfci in self.sfcis.items():
            slo = SLO(availability=0, latency=0, throughput=0, dropRate=0)
            slo.availability = 1.0 - 0.0005 * random.random()
            directions = sfci['sfc'].directions
            primaryForwardingPath = sfci['sfci'].forwardingPathSet.primaryForwardingPath
            for direction in directions:
                dirID = direction['ID']
                if dirID == 0:
                    pathlist = primaryForwardingPath[DIRECTION1_PATHID_OFFSET]
                else:
                    pathlist = primaryForwardingPath[DIRECTION2_PATHID_OFFSET]
                dropRate = 0
                for stage, path in enumerate(pathlist):
                    for hop, (_, srcID) in enumerate(path):
                        if hop != len(path) - 1:
                            dstID = path[hop + 1][1]
                            if srcID == dstID:
                                continue
                            if (srcID, dstID) in self.serverLinks:  # server -> switch, switchID is server
                                link = self.serverLinks[(srcID, dstID)]['link']  # type: Link
                            else:  # switch -> switch
                                link = self.links[(srcID, dstID)]['link']
                            link_bw = links[(srcID, dstID)]
                            link.utilization = min(1.0, link_bw / 1024 / link.bandwidth)
                            dropRate = max(dropRate, link_bw / 1024 / link.bandwidth - 1.0)
                            slo.latency += performanceModel.getLatencyOfLink(link, link.utilization)
                dropRate += 0.001 * random.random()
                slo.dropRate += dropRate / 2.0
                bw = sfcis[sfciID][dirID]
                slo.throughput += bw * (1.0 - dropRate) / 1024.0

            sfci['sfci'].sloRealTimeValue = slo

        torNum = len(self.torPaths)
        tm = np.random.uniform(0.0, MAX_BG_BW, (torNum, torNum))
        for i in range(torNum):
            for j in range(torNum):
                if i == j:
                    continue
                if CHECK_CONNECTIVITY:
                    paths = self.valid_paths(i, j)
                else:
                    paths = self.torPaths[i][j]
                parts = len(paths)
                for path in paths:
                    for link in path:
                        link.utilization = min(tm[i][j] / parts / (link.bandwidth * 1024) + link.utilization, 1.0)

    def valid_paths(self, i, j):
        ret = []
        paths = self.torPaths[i][j]
        for path in paths:
            if not self.switches[path[0].srcID]['Active']:
                continue
            for link in path:
                if not self.switches[link.dstID]['Active'] or not self.links[(link.srcID, link.dstID)]['Active']:
                    break
            else:
                ret.append(path)
        return ret
