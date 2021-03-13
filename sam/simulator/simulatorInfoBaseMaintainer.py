#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
store dcn information
e.g. switch, server, link, sfc, sfci, vnfi, flow
'''

import uuid

from sam.base.pickleIO import PickleIO
from sam.measurement.dcnInfoBaseMaintainer import DCNInfoBaseMaintainer


class SimulatorInfoBaseMaintainer(DCNInfoBaseMaintainer):
    def __init__(self):
        super(SimulatorInfoBaseMaintainer, self).__init__()
        self.pIO = PickleIO()
        self.links = {}
        self.switches = {}
        self.servers = {}

    def loadTopology(self, topoFilePath):
        self.topologyDict = self.pIO.readPickleFile(topoFilePath)
        # more details in /sam/simulator/test/readme.md
        self.links = self.topologyDict["links"]
        self.switches = self.topologyDict["switches"]
        self.servers = self.topologyDict["servers"]

    def turnOffSwitch(self, switch):
        pass
        # CLI > switch 3 down

    def turnOnSwitch(self, switch):
        pass
        # CLI > switch 3 up

    def turnOffLink(self, link):
        pass

    def turnOnLink(self, link):
        pass

    def turnOnServer(self, server):
        pass

    def turnOffServer(self, server):
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
