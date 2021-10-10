#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os

from sam.base.server import *
from sam.base.link import *
from sam.base.xibMaintainer import XInfoBaseMaintainer
from sam.base.socketConverter import SocketConverter


class ServerInfoBaseMaintainer(XInfoBaseMaintainer):
    def __init__(self):
        super(ServerInfoBaseMaintainer, self).__init__()
        self._servers = {}  # [zoneName][serverID] = {'server':server, 'Active':True/False, 'timestamp':time, 'status':none}

        self._serversReservedResources = {} # [zoneName][serverID] = {'bandwidth':bw, 'cores':cpu, 'memory':mem}

        self._sc = SocketConverter()


    def _initServerTable(self):
        if not self.dbA.hasTable("Measurer", "Server"):
            self.dbA.createTable("Server",
                """
                ID INT UNSIGNED AUTO_INCREMENT,
                ZONE_NAME VARCHAR(100) NOT NULL,
                SERVER_UUID VARCHAR(36),
                SERVER_TYPE VARCHAR(100) NOT NULL,
                IP_ADDRESS VARCHAR(256) NOT NULL,
                TOTAL_CPU_CORE SMALLINT,
                TOTAL_MEMORY FLOAT,
                TOTAL_NIC_BANDWIDTH FLOAT,
                PICKLE BLOB,
                submission_time TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY ( ID )
                """
                )

    def hasServer(self, serverUUID, zoneName):
        results = self.dbA.query("Measurer", " SERVER_UUID ",
                    " SERVER_UUID = '{0}' AND ZONE_NAME = '{1}'".format(serverUUID, zoneName))
        if results != ():
            return True
        else:
            return False

    def addServer(self, server, zoneName):
        if not self.hasServer(server.getServerID(), zoneName):
            self.dbA.insert("Measurer",
                " ZONE_NAME, SERVER_UUID, SERVER_TYPE, IP_ADDRESS, TOTAL_CPU_CORE, " \
                " TOTAL_MEMORY, TOTAL_NIC_BANDWIDTH ",
                "'{0}'".format(zoneName,
                                server.getServerID(),
                                server.getServerType(),
                                server.getControlNICIP(),
                                server.getMaxCores(),
                                server.getMaxMemory(),
                                server.getNICBandwidth()
                ))

    def delServer(self, serverUUID, zoneName):
        if self.hasServer(serverUUID, zoneName):
            self.dbA.delete("Measurer",
                " ZONE_NAME = '{0}' AND SERVER_UUID = '{1}'".format(zoneName, serverUUID))

    def getAllServer(self):
        results = self.dbA.query("Measurer", " SERVER_UUID ")
        serverList = []
        for server in results:
            serverList.append(server)
        return serverList

    def updateServersInAllZone(self, servers):
        self._servers = servers

    def updateServersByZone(self, servers, zoneName):
        self._servers[zoneName] = servers

    def getServersInAllZone(self):
        return self._servers

    def getServersByZone(self, zoneName):
        return self._servers[zoneName]

    def getServer(self, serverID, zoneName):
        return self._servers[zoneName][serverID]['server']

    def isServerID(self, nodeID):
        servers = self.getServersInAllZone()
        for serversInAZoneDict in servers.values():
            if nodeID in serversInAZoneDict.keys():
                return True
        else:
            return False


    def reserveServerResources(self, serverID, reservedCores, reservedMemory,
            reservedBandwidth, zoneName):
        if not self._serversReservedResources.has_key(zoneName):
            self._serversReservedResources[zoneName] = {}
        if not self._serversReservedResources[zoneName].has_key(serverID):
            self._serversReservedResources[zoneName][serverID] = {}
            self._serversReservedResources[zoneName][serverID]["cores"] = reservedCores
            self._serversReservedResources[zoneName][serverID]["memory"] = reservedMemory
            self._serversReservedResources[zoneName][serverID]["bandwidth"] = reservedBandwidth
        else:
            cores = self._serversReservedResources[zoneName][serverID]["cores"]
            memory = self._serversReservedResources[zoneName][serverID]["memory"]
            bandwidth = self._serversReservedResources[zoneName][serverID]["bandwidth"]
            self._serversReservedResources[zoneName][serverID]["cores"] = cores \
                + reservedCores
            self._serversReservedResources[zoneName][serverID]["memory"] = memory \
                + reservedMemory
            self._serversReservedResources[zoneName][serverID]["bandwidth"] = bandwidth \
                + reservedBandwidth

    def releaseServerResources(self, serverID, releaseCores, releaseMemory,
            releaseBandwidth, zoneName):
        if not self._serversReservedResources.has_key(zoneName):
            self._serversReservedResources[zoneName] = {}
        if not self._serversReservedResources.has_key(serverID):
            raise ValueError("Unknown serverID:{0}".format(serverID))
        else:
            cores = self._serversReservedResources[zoneName][serverID]["cores"]
            memory = self._serversReservedResources[zoneName][serverID]["memory"]
            bandwidth = self._serversReservedResources[zoneName][serverID]["bandwidth"]
            self._serversReservedResources[zoneName][serverID]["cores"] = cores \
                - releaseCores
            self._serversReservedResources[zoneName][serverID]["memory"] = memory \
                - releaseMemory
            self._serversReservedResources[zoneName][serverID]["bandwidth"] = bandwidth \
                - releaseBandwidth

    def getServerReservedResources(self, serverID, zoneName):
        if not self._serversReservedResources.has_key(zoneName):
            self._serversReservedResources[zoneName] = {}
        if not self._serversReservedResources.has_key(serverID):
            # raise ValueError("Unknown serverID:{0}".format(serverID))
            self.reserveServerResources(serverID, 0, 0, 0, zoneName)
        cores = self._serversReservedResources[zoneName][serverID]["cores"]
        memory = self._serversReservedResources[zoneName][serverID]["memory"]
        bandwidth = self._serversReservedResources[zoneName][serverID]["bandwidth"]
        return (cores, memory, bandwidth)

    def getServerResidualResources(self, serverID, zoneName):
        reservedResource = self.getServerReservedResources(serverID, zoneName)
        (reseCores, reseMemory, reseBandwidth) = reservedResource
        server = self.getServer(serverID, zoneName)
        coreCapacity = server.getMaxCores()
        memoryCapacity = server.getMaxMemory()
        bandwidthCapacity = server.getNICBandwidth()
        return (coreCapacity-reseCores, 
            memoryCapacity-reseMemory, bandwidthCapacity-reseBandwidth)

    def hasEnoughServerResources(self, serverID, expectedResource, zoneName):
        (expectedCores, expectedMemory, expectedBandwidth) = expectedResource
        server = self._servers[zoneName][serverID]['server']
        # (coresCapacity, memoryCapacity, bandwidthCapacity) = self.getServersResourcesCapacity(
        #     [server], zoneName)
        serverID = server.getServerID()
        (avaCores, avaMemory, avaBandwidth) = self.getServerResidualResources(
            serverID, zoneName)
        if (expectedCores <= avaCores
                and expectedMemory <= avaMemory
                and expectedBandwidth <= avaBandwidth):
            return True
        else:

            # print("expectedCores:{0}\texpectedMemory:{1}\texpectedBandwidth:{2}\n"
            #     "avaCores:{3}\tavaMemory:{4}\tavaBandwidth:{5}\n".format(
            #         expectedCores, expectedMemory, expectedBandwidth,
            #         avaCores, avaMemory, avaBandwidth))
            # os.system("pause")

            return False


