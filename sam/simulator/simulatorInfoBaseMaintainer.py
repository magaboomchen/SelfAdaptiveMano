#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
store dcn information
e.g. switch, server, link, sfc, sfci, vnfi, flow
'''

import uuid

from sam.base.pickleIO import PickleIO
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
            serverInfo['switchID']=[]
            server=serverInfo['server']
            DatapathIP=server.getDatapathNICIP()
            for switchID, switchInfo in self.switches.items():
                switch=switchInfo['switch']
                switchNet=switch.lanNet
                if self.sc.isLANIP(DatapathIP, switchNet):
                    break
            else:
                continue
            bw=server.getNICBandwidth()
            self.serverLinks[(serverID, switchID)]={'link':Link(serverID, switchID, bw), 'Active':True, 'Status':None}
            self.serverLinks[(switchID, serverID)]={'link':Link(switchID, serverID, bw), 'Active':True, 'Status':None}
            serverInfo['switchID'].append(switchID)

    def turnOffSwitch(self, switchID):
        pass
        # CLI > switch 3 down

    def turnOnSwitch(self, switchID):
        pass
        # CLI > switch 3 up

    def turnOffLink(self, srcID, dstID):
        pass

    def turnOnLink(self, srcID, dstID):
        pass

    def turnOnServer(self, serverID):
        pass

    def turnOffServer(self, serverID):
        pass

    def getSFCIFlowIdentifierDict(self, sfci, stageIndex):
        pass
        # Flow Identifier is a unique id of each flow
        # E.g. IPv4 destination address of a flow is an identifier
        # Flow's IdentifierDict refer to sam/base/flow.py
        # <object routingMorphic> = <object sfc>.routingMorphic
        # identifierDict = <object routingMorphic>.getIdentifierDict()
        # identifierDict['value'] = <object routingMorphic>.encodeIdentifierForSFC(sfciID, vnfID)
        # identifierDict['humanReadble'] = <object routingMorphic>.value2HumanReadable(identifierDict['value'])
        # flow(identifierDict)
