#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.server import *
from sam.base.link import *
from sam.base.socketConverter import SocketConverter
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.measurement.serverInfoBaseMaintainer import ServerInfoBaseMaintainer
from sam.measurement.switchInfoBaseMaintainer import SwitchInfoBaseMaintainer
from sam.measurement.linkInfoBaseMaintainer import LinkInfoBaseMaintainer
from sam.measurement.vnfiInfoBaseMaintainer import VNFIInfoBaseMaintainer

# TODO : test


class DCNInfoBaseMaintainer(ServerInfoBaseMaintainer,
                            SwitchInfoBaseMaintainer,
                            LinkInfoBaseMaintainer,
                            VNFIInfoBaseMaintainer):
    def __init__(self):
        super(DCNInfoBaseMaintainer, self).__init__()
        # can't implement logger, because it doesn't support deepcopy
        # logConfigur = LoggerConfigurator(__name__, './log',
        #     'DCNInfoBaseMaintainer.log', level='debug')
        # self.logger = logConfigur.getLogger()
        self._sc = SocketConverter()
        self.isDBEnable = False

    def enableDataBase(self, host, user, passwd, reInitialTable=False):
        self.addDatabaseAgent(host, user, passwd)
        if not self.dbA.isConnectingDB():
            self.dbA.connectDB(db = "Measurer")
        if reInitialTable:
            self.dbA.dropTable("Server")
            self.dbA.dropTable("Switch")
            self.dbA.dropTable("Link")
        self._initServerTable()
        self._initSwitchTable()
        self._initLinkTable()
        self.isDBEnable = True

    def updateSwitch2ServerLinksByZone(self, zoneName):
        servers = self.getServersByZone(zoneName)
        for serverID, serverInfoDict in servers.items():
            server = serverInfoDict['server']
            bw = server.getNICBandwidth()
            switch = self.getConnectedSwitch(serverID, zoneName)
            switchID = switch.switchID
            linkID1 = (serverID, switchID)
            self._links[zoneName][linkID1] = {
                'link': Link(serverID, switchID, bandwidth=bw),
                'Active': True
                }

            linkID2 = (switchID, serverID)
            self._links[zoneName][linkID2] = {
                'link': Link(switchID, serverID, bandwidth=bw),
                'Active': True
                }

    def isLinkConnectServer(self, srcID, dstID):
        if self.isServerID(srcID) or self.isServerID(dstID):
            return True
        else:
            return False

    def isLinkConnectTwoSwitches(self, srcID, dstID):
        if self.isSwitchID(srcID) or self.isSwitchID(dstID):
            return True
        else:
            return False

    def getConnectedSwitch(self, serverID, zoneName):
        for switchID,switchInfoDict in self._switches[zoneName].items():
            switch = switchInfoDict['switch']
            if self.isServerConnectSwitch(switchID, serverID, zoneName):
                return switch

    def isServerConnectSwitch(self, switchID, serverID, zoneName):
        switch = self._switches[zoneName][switchID]['switch']
        lanNet = switch.lanNet
        server = self._servers[zoneName][serverID]['server']
        dpIP = server.getDatapathNICIP()
        if self._sc.isLANIP(dpIP, lanNet):
            return True
        else:
            return False

    def getConnectedServers(self, switchID, zoneName):
        servers = []
        for serverID,serverInfoDict in self._servers[zoneName].items():
            server = serverInfoDict['server']
            if self.isServerConnectSwitch(switchID, serverID, zoneName):
                servers.append(server)
        return servers

    def getConnectedNFVIs(self, switchID, zoneName, abandonServerIDList=[]):
        servers = []
        for serverID,serverInfoDict in self._servers[zoneName].items():
            server = serverInfoDict['server']
            if (self.isServerConnectSwitch(switchID, serverID, zoneName) 
                    and server.getServerType() == SERVER_TYPE_NFVI
                    and serverID not in abandonServerIDList):
                servers.append(server)
        return servers

    def getServersReservedResources(self, serverList, zoneName):
        coresSum = 0
        memorySum = 0
        bandwidthSum = 0
        for server in serverList:
            serverID = server.getServerID()
            if not self._serversReservedResources.has_key(zoneName):
                self._serversReservedResources[zoneName] = {}
            if not self._serversReservedResources.has_key(serverID):
                self.reserveServerResources(serverID, 0, 0, 0, zoneName)
            (cores, memory, bandwidth) = self.getServerReservedResources(
                serverID, zoneName)
            coresSum = coresSum + cores
            memorySum = memorySum + memory
            bandwidthSum = bandwidthSum + bandwidth
        return (coresSum, memorySum, bandwidthSum)

    def getServersResourcesCapacity(self, serverList, zoneName):
        coresSum = 0
        memorySum = 0
        bandwidthSum = 0
        for server in serverList:
            serverID = server.getServerID()
            if not self._serversReservedResources.has_key(zoneName):
                self._serversReservedResources[zoneName] = {}
            if not self._serversReservedResources.has_key(serverID):
                self.reserveServerResources(serverID, 0, 0, 0, zoneName)
            cores = server.getMaxCores()
            memory = server.getMaxMemory()
            bandwidth = server.getNICBandwidth()
            coresSum = coresSum + cores
            memorySum = memorySum + memory
            bandwidthSum = bandwidthSum + bandwidth
        return (coresSum, memorySum, bandwidthSum)

    def hasEnoughNPoPServersResources(self, nodeID,
            expectedCores, expectedMemory, expectedBandwidth, zoneName, abandonServerIDList=[]):
        # cores and memory resources
        switch = self.getSwitch(nodeID, zoneName)
        servers = self.getConnectedNFVIs(nodeID, zoneName, abandonServerIDList)
        (coresSum, memorySum, bandwidthSum) = self.getServersReservedResources(
            servers, zoneName)
        (coreCapacity, memoryCapacity, bandwidthCapacity) = self.getServersResourcesCapacity(
            servers, zoneName)
        residualCores = coreCapacity - coresSum
        residualMemory = memoryCapacity - memorySum
        residualBandwidth = bandwidthCapacity - bandwidthSum
        # self.logger.debug(
        #     "servers resource, residualCores:{0}, \
        #        residualMemory:{1}".format(
        #         residualCores, residualMemory
        #     ))

        # print("servers resource, residualCores:{0}, residualMemory:{1}, "
        #     "memoryCapacity:{2}".format(
        #     residualCores, residualMemory, memoryCapacity))

        if (residualCores > expectedCores 
                and residualMemory > expectedMemory
                and residualBandwidth > expectedBandwidth):
            return True
        else:
            return False

    def getNPoPServersCapacity(self, switchID, zoneName):
        # for the sake of simplicity, we only use cpu core as capacity
        coreNum = 0
        for serverID, serverInfoDict in self.getServersByZone(zoneName).items():
            server = serverInfoDict['server']
            if (self.isServerConnectSwitch(switchID, serverID, zoneName)
                and server.getServerType() != SERVER_TYPE_CLASSIFIER):
                coreNum = coreNum \
                    + self.getServerResidualResources(serverID,
                        zoneName)[0] # server.getMaxCores()
        return coreNum

    def getAllZone(self):
        zoneList = []
        for zone in self._servers.keys():
            if zone not in zoneList:
                zoneList.append(zone)

        for zone in self._switches.keys():
            if zone not in zoneList:
                zoneList.append(zone)

        for zone in self._links.keys():
            if zone not in zoneList:
                zoneList.append(zone)

        return zoneList

    def updateByNewDib(self, newDib):
        self.updateServersInAllZone(newDib.getServersInAllZone())
        self.updateSwitchesInAllZone(newDib.getSwitchesInAllZone())
        self.updateLinksInAllZone(newDib.getLinksInAllZone())
        self.updateVnfisInAllZone(newDib.getVnfisInAllZone())

    def getClassifierBySwitch(self, switch, zoneName):
        for serverInfoDict in self.getServersByZone(zoneName).values():
            server = serverInfoDict['server']
            ip = server.getDatapathNICIP()
            serverType = server.getServerType()
            if self._sc.isLANIP(ip, switch.lanNet) and \
                serverType == SERVER_TYPE_CLASSIFIER:
                return server
        else:
            raise ValueError("Find classifier of switchID {0} failed".format(switch.switchID))

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)
