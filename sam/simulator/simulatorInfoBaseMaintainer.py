#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
store dcn information
e.g. switch, server, link, sfc, sfci, vnfi, flow
'''

import uuid

from sam.base.pickleIO import PickleIO
from sam.base.sfc import SFC, SFCI
from sam.measurement.dcnInfoBaseMaintainer import DCNInfoBaseMaintainer
from sam.base.link import Link
from re import match
from sam.base.socketConverter import SocketConverter


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

    def reset(self):
        self.links.clear()
        self.switches.clear()
        self.servers.clear()
        self.serverLinks.clear()
        self.sfcs.clear()
        self.sfcis.clear()
        self.flows.clear()

    def loadTopology(self, topoFilePath):
        self.reset()
        self.topologyDict = self.pIO.readPickleFile(topoFilePath)
        # more details in /sam/simulator/test/readme.md

        self.links.update(self.topologyDict["links"])
        self.switches.update(self.topologyDict["switches"])
        self.servers.update(self.topologyDict["servers"])

        for serverID, serverInfo in self.servers.items():
            serverInfo['uplink2NUMA'] = {}
            serverInfo['Status'] = {'coreAssign': {}}

        for switchID, switchInfo in self.switches.items():
            switchInfo['Status'] = {'nextHop': {}}
            switchInfo['switch'].tcamUsage = 0

        for (srcNodeID, dstNodeID), linkInfo in self.links.items():
            linkInfo['Status'] = {'usedBy': set()}

        for serverID, serverInfo in self.servers.items():
            server = serverInfo['server']
            DatapathIP = server.getDatapathNICIP()
            for switchID, switchInfo in self.switches.items():
                switch = switchInfo['switch']
                switchNet = switch.lanNet
                if self.sc.isLANIP(DatapathIP, switchNet):
                    break
            else:
                continue
            bw = server.getNICBandwidth()
            self.serverLinks[(serverID, switchID)] = {'link': Link(serverID, switchID, bw), 'Active': True,
                                                      'Status': None}
            self.serverLinks[(switchID, serverID)] = {'link': Link(switchID, serverID, bw), 'Active': True,
                                                      'Status': None}
            serverInfo['uplink2NUMA'][switchID] = 0

        for (srcNodeID, dstNodeID), linkInfo in self.serverLinks.items():
            linkInfo['Status'] = {'usedBy': set()}

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
