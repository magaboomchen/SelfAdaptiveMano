#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
store dcn information
e.g. switch, server, link, sfc, sfci, vnfi
'''

from sam.base.xibMaintainer import XInfoBaseMaintainer


class SimulatorInfoBaseMaintainer(XInfoBaseMaintainer):
    def __init__(self):
        super(SimulatorInfoBaseMaintainer, self).__init__()
        pass

    def addSwitch(self, switch):
        pass

    def addServer(self, server):
        pass

    def addLink(self, link):
        pass

    def addTopo(self, filePath):
        pass

    def addSFC(self):
        pass

    def addSFCI(self):
        pass

    def getEnd2EndLatency(self, sfciID):
        pass

    def getMaxEnd2EndLatency(self, sfciID):
        pass

    def getFIBNumUncompressed(self, switchID):
        pass

    def getAllFIBNumUncompressed(self):
        pass

    def getFIBNumCompressed(self, switchID):
        pass

    def getAllFIBNumCompressed(self):
        pass

    def getLinkBandwidthUtilization(self):
        pass

    def getServerResourceUtilization(self, serverID):
        pass

    def getAllServerResourceUtilization(self):
        pass
