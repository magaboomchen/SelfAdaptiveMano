#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.xibMaintainer import XInfoBaseMaintainer
from sam.base.socketConverter import SocketConverter

# TODO : test


class DCNInfoBaseMaintainer(XInfoBaseMaintainer):
    def __init__(self, *args, **kwargs):
        super(DCNInfoBaseMaintainer, self).__init__(*args, **kwargs)
        self._servers = {}
        self._switches = {}
        self._links = {}
        self._vnfis = {}

        self._serversReservedResources = {}
        self._switchesReservedResources = {}
        self._linksReservedResources = {}
        self._vnfisReservedResources = {}
        
        self._sc = SocketConverter()

    def updateServersInAllZone(self, servers):
        self._servers = servers

    def updateServersByZone(self, servers, zoneName):
        self._servers[zoneName] = servers

    def updateSwitchesInAllZone(self, switches):
        self._switches = switches

    def updateSwitchesByZone(self, switches, zoneName):
        self._switches[zoneName] = switches

    def updateLinksInAllZone(self, links):
        self._links = links

    def updateLinksByZone(self, links, zoneName):
        self._links[zoneName] = links

    def updateVnfisInAllZone(self, vnfis):
        self._vnfis = vnfis

    def updateVnfisByZone(self, vnfis, zoneName):
        self._vnfis[zoneName] = vnfis

    def getServersInAllZone(self):
        return self._servers

    def getServersByZone(self, zoneName):
        return self._servers[zoneName]

    def getSwitchesInAllZone(self):
        return self._switches

    def getSwitchesByZone(self, zoneName):
        return self._switches[zoneName]

    def getLinksInAllZone(self):
        return self._links

    def getLinksByZone(self, zoneName):
        return self._links[zoneName]

    def getVnfisInAllZone(self):
        return self._vnfis

    def getVnfisByZone(self, zoneName):
        return self._vnfis[zoneName]

    def getServer(self, serverID, zoneName):
        return self._servers[zoneName][serverID]

    def getConnectedSwitch(self, serverID, zoneName):
        for switchID,switch in self._switches[zoneName].items():
            if self.isServerConnectSwitch(switchID, serverID, zoneName):
                return switch

    def isServerConnectSwitch(self, switchID, serverID, zoneName):
        switch = self._switches[zoneName][switchID]
        lanNet = switch.lanNet
        server = self._servers[zoneName][serverID]
        # ctIP = server.getControlNICIP()
        dpIP = server.getDatapathNICIP()
        if self._sc.isLANIP(dpIP, lanNet):
            return True
        else:
            return False

    def getConnectedServers(self, switchID, zoneName):
        servers = []
        for serverID,server in self._servers[zoneName].items():
            if self.isServerConnectSwitch(switchID, serverID, zoneName):
                servers.append(server)
        return servers

    def getSwitch(self, switchID, zoneName):
        return self._switches[zoneName][switchID]

    def getLink(self, srcID, dstID, zoneName):
        return self._links[zoneName][(srcID, dstID)]

    def reserveServerResources(self, serverID, reservedCores, reservedMemory,
        zoneName):
        if not self._serversReservedResources.has_key(zoneName):
            self._serversReservedResources[zoneName] = {}
        if not self._serversReservedResources[zoneName].has_key(serverID):
            self._serversReservedResources[zoneName][serverID] = {}
            self._serversReservedResources[zoneName][serverID]["cores"] = reservedCores
            self._serversReservedResources[zoneName][serverID]["memory"] = reservedMemory
        else:
            cores = self._serversReservedResources[zoneName][serverID]["cores"]
            memory = self._serversReservedResources[zoneName][serverID]["memory"]
            self._serversReservedResources[zoneName][serverID]["cores"] = cores \
                + reservedCores
            self._serversReservedResources[zoneName][serverID]["memory"] = memory \
                + reservedMemory

    def releaseServerResources(self, serverID, releaseCores, releaseMemory,
        zoneName):
        if not self._serversReservedResources.has_key(zoneName):
            self._serversReservedResources[zoneName] = {}
        if not self._serversReservedResources.has_key(serverID):
            raise ValueError("Unknown serverID:{0}".format(serverID))
        else:
            cores = self._serversReservedResources[zoneName][serverID]["cores"]
            memory = self._serversReservedResources[zoneName][serverID]["memory"]
            self._serversReservedResources[zoneName][serverID]["cores"] = cores \
                - releaseCores
            self._serversReservedResources[zoneName][serverID]["memory"] = memory \
                - releaseMemory

    def getServerReservedResources(self, serverID, zoneName):
        if not self._serversReservedResources.has_key(zoneName):
            self._serversReservedResources[zoneName] = {}
        if not self._serversReservedResources.has_key(serverID):
            # raise ValueError("Unknown serverID:{0}".format(serverID))
            self.reserveServerResources(serverID, 0, 0, zoneName)
        cores = self._serversReservedResources[zoneName][serverID]["cores"]
        memory = self._serversReservedResources[zoneName][serverID]["memory"]
        return (cores, memory)

    def getServersReservedResources(self, serverList, zoneName):
        coresSum = 0
        memorySum = 0
        for server in serverList:
            serverID = server.getServerID()
            if not self._serversReservedResources.has_key(zoneName):
                self._serversReservedResources[zoneName] = {}
            if not self._serversReservedResources.has_key(serverID):
                self.reserveServerResources(serverID, 0, 0, zoneName)
            (cores, memory) = self.getServerReservedResources(
                serverID, zoneName)
            coresSum = coresSum + cores
            memorySum = memorySum + memory
        return (coresSum, memorySum)

    def getServersResourcesCapacity(self, serverList, zoneName):
        coresSum = 0
        memorySum = 0
        for server in serverList:
            serverID = server.getServerID()
            if not self._serversReservedResources.has_key(zoneName):
                self._serversReservedResources[zoneName] = {}
            if not self._serversReservedResources.has_key(serverID):
                self.reserveServerResources(serverID, 0, 0, zoneName)
            cores = server.getMaxCores()
            memory = server.getMaxMemory()
            coresSum = coresSum + cores
            memorySum = memorySum + memory
        return (coresSum, memorySum)

    def reserveSwitchResource(self, switchID, reservedTcamUsage, zoneName):
        if not self._switchesReservedResources.has_key(zoneName):
            self._switchesReservedResources[zoneName] = {}
        if not self._switchesReservedResources[zoneName].has_key(switchID):
            self._switchesReservedResources[zoneName][switchID] = {}
            self._switchesReservedResources[zoneName][switchID]["tcamUsage"] = reservedTcamUsage
        else:
            tcamUsage = self._switchesReservedResources[zoneName][switchID]["tcamUsage"]
            self._switchesReservedResources[zoneName][switchID]["tcamUsage"] = tcamUsage \
                + reservedTcamUsage

    def releaseSwitchResource(self, switchID, releaseTcamUsage, zoneName):
        if not self._switchesReservedResources.has_key(zoneName):
            self._switchesReservedResources[zoneName] = {}
        if not self._switchesReservedResources[zoneName].has_key(switchID):
            raise ValueError("Unknown switchID:{0}".format(switchID))
        else:
            tcamUsage = self._switchesReservedResources[zoneName][switchID]["tcamUsage"]
            self._switchesReservedResources[zoneName][switchID]["tcamUsage"] = tcamUsage \
                - releaseTcamUsage

    def getSwitchReservedResource(self, switchID, zoneName):
        if not self._switchesReservedResources.has_key(zoneName):
            self._switchesReservedResources[zoneName] = {}
        if not self._switchesReservedResources[zoneName].has_key(switchID):
            # raise ValueError("Unknown switchID:{0}".format(switchID))
            self.reserveSwitchResource(switchID, 0, zoneName)
        return self._switchesReservedResources[zoneName][switchID]["tcamUsage"]

    def reserveLinkResource(self, srcID, dstID, reservedBandwidth, zoneName):
        if not self._linksReservedResources.has_key(zoneName):
            self._linksReservedResources[zoneName] = {}
        linkKey = (srcID, dstID)
        if not self._linksReservedResources[zoneName].has_key(linkKey):
            self._linksReservedResources[zoneName][linkKey] = {}
            self._linksReservedResources[zoneName][linkKey]["bandwidth"] = reservedBandwidth
        else:
            bandwidth = self._linksReservedResources[zoneName][linkKey]["bandwidth"]
            self._linksReservedResources[zoneName][linkKey]["bandwidth"] = bandwidth \
                + reservedBandwidth

    def releaseLinkResource(self, srcID, dstID, releaseBandwidth, zoneName):
        if not self._linksReservedResources.has_key(zoneName):
            self._linksReservedResources[zoneName] = {}
        linkKey = (srcID, dstID)
        if not self._linksReservedResources[zoneName].has_key(linkKey):
            raise ValueError("Unknown linkKey:{0}".format(linkKey))
        else:
            bandwidth = self._linksReservedResources[zoneName][linkKey]["bandwidth"]
            self._linksReservedResources[zoneName][linkKey]["bandwidth"] = bandwidth \
                - releaseBandwidth

    def getLinkReservedResource(self, srcID, dstID, zoneName):
        if not self._linksReservedResources.has_key(zoneName):
            self._linksReservedResources[zoneName] = {}
        linkKey = (srcID, dstID)
        if not self._linksReservedResources[zoneName].has_key(linkKey):
            # raise ValueError("Unknown linkKey:{0}".format(linkKey))
            self.reserveLinkResource(srcID, dstID, 0, zoneName)
        return self._linksReservedResources[zoneName][linkKey]["bandwidth"]

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)
