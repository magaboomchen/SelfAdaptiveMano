#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
store dcn information
e.g. switch, server, link, sfc, sfci, vnfi, flow
'''
import copy
import math

from sam.base.pickleIO import PickleIO
from sam.base.sfc import SFC, SFCI
from sam.measurement.dcnInfoBaseMaintainer import DCNInfoBaseMaintainer
from sam.base.link import Link
from sam.base.socketConverter import SocketConverter
from sam.base.server import Server


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
            utilization = [0] * len(server._coreUtilization)
            for singleCpu in distribution:
                for core in singleCpu:
                    if cpu <= 0:
                        break
                    usage = min(cpu, 100)
                    utilization[core] = usage
                    cpu -= usage
            server._coreUtilization = utilization

            pageSize = server.getHugepagesSize()
            pageUsage = reduce(lambda x, y: x + y,
                               [int(math.ceil(process['mem'] * 1024 / pageSize)) for process in processes])
            server._hugepagesFree = server.getHugepagesTotal() - pageUsage
