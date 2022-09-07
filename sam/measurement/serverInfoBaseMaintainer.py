#!/usr/bin/python
# -*- coding: UTF-8 -*-

from typing import Dict, Union, Any

from sam.base.server import Server
from sam.base.xibMaintainer import XInfoBaseMaintainer
from sam.base.messageAgent import SIMULATOR_ZONE, TURBONET_ZONE


class ServerInfoBaseMaintainer(XInfoBaseMaintainer):
    def __init__(self):
        super(ServerInfoBaseMaintainer, self).__init__()
        self._servers = {}  # type: Dict[Union[TURBONET_ZONE, SIMULATOR_ZONE], Dict[int, Dict[str, Any]]]
        # [zoneName][serverID] = {'server':server, 'Active':True, 'timestamp':datetime, 'Status':none}
        self._serversReservedResources = {} # [zoneName][serverID] = {'bandwidth':bw, 'cores':cpu, 'memory':mem}
        self.isServerInfoInDB = False

    def _initServerTable(self):
        # self.dbA.dropTable("Server")
        if not self.dbA.hasTable("Measurer", "Server"):
            self.dbA.createTable("Server",
                """
                ID INT UNSIGNED AUTO_INCREMENT,
                ZONE_NAME VARCHAR(100) NOT NULL,
                SERVER_ID SMALLINT,
                SERVER_TYPE VARCHAR(100),
                IP_ADDRESS VARCHAR(256),
                TOTAL_CPU_CORE SMALLINT,
                TOTAL_MEMORY FLOAT,
                TOTAL_NIC_BANDWIDTH FLOAT,
                PICKLE BLOB,
                submission_time TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY ( ID )
                """
                )
        self.isServerInfoInDB = True

    def hasServer(self, serverID, zoneName):
        # type: (int, Union[SIMULATOR_ZONE, TURBONET_ZONE]) -> None
        if self.isServerInfoInDB:
            results = self.dbA.query("Server", " SERVER_ID ",
                        " SERVER_ID = '{0}' AND ZONE_NAME = '{1}'".format(
                                                        serverID, zoneName))
            if results != ():
                return True
            else:
                return False
        else:
            if serverID in self._servers[zoneName].keys():
                return True
            else:
                return False

    def addServer(self, server, zoneName):
        # type: (Server, Union[SIMULATOR_ZONE, TURBONET_ZONE]) -> None
        if self.isServerInfoInDB:
            if not self.hasServer(server.getServerID(), zoneName):
                self.dbA.insert("Server",
                    " ZONE_NAME, SERVER_ID, SERVER_TYPE, IP_ADDRESS, TOTAL_CPU_CORE, " \
                    " TOTAL_MEMORY, TOTAL_NIC_BANDWIDTH, PICKLE ",
                        (   
                            zoneName,
                            server.getServerID(),
                            server.getServerType(),
                            server.getControlNICIP(),
                            server.getMaxCores(),
                            server.getMaxMemory(),
                            server.getNICBandwidth(),
                            self.pIO.obj2Pickle(server)
                        )
                    )
        else:
            if zoneName not in self._servers:
                self._servers[zoneName] = {}
            serverID = server.getServerID()
            self._servers[zoneName][serverID] = {'server':server, 'Active':True, 'timestamp':None, 'Status':None}

    def delServer(self, serverID, zoneName):
        # type: (int, Union[SIMULATOR_ZONE, TURBONET_ZONE]) -> None
        if self.isServerInfoInDB:
            if self.hasServer(serverID, zoneName):
                self.dbA.delete("Server",
                    " ZONE_NAME = '{0}' AND SERVER_ID = '{1}'".format(zoneName, serverID))
        else:
            del self._servers[zoneName][serverID]

    def getAllServer(self):
        serverList = []
        if self.isServerInfoInDB:
            results = self.dbA.query("Server",
                            " ID, ZONE_NAME, SERVER_ID, SERVER_TYPE, IP_ADDRESS, TOTAL_CPU_CORE, " \
                            " TOTAL_MEMORY, TOTAL_NIC_BANDWIDTH, PICKLE ")
            for server in results:
                serverList.append(server)
        else:
            for zoneName, serversInfo in self._servers.items():
                for serverID, serverInfo in serversInfo.items():
                    serverList.append(serverInfo['server'])
        return serverList

    def updateServersInAllZone(self, servers):
        self._servers = servers

    def updateServersByZone(self, servers, zoneName):
        if zoneName not in self._servers.keys():
            self._servers[zoneName] = {}
        self._servers[zoneName] = servers

    def updateServerState(self, serverID, zoneName, state):
        self._servers[zoneName][serverID]['Active'] = state

    def getServersInAllZone(self):
        return self._servers

    def getServersByZone(self, zoneName, pruneInactiveServers=False):
        if pruneInactiveServers:
            servers = {}
            for serverID, serverInfoDict in self._servers[zoneName].items():
                if serverInfoDict['Active']:
                    servers[serverID] = serverInfoDict
            return servers
        else:
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

    def isServerActive(self, serverID, zoneName):
        # type: (int, str) -> bool
        return self._servers[zoneName][serverID]['active']

    def reserveServerResources(self, serverID, reservedCores, reservedMemory,
            reservedBandwidth, zoneName):
        if not (zoneName in self._serversReservedResources):
            self._serversReservedResources[zoneName] = {}
        if not (serverID in self._serversReservedResources[zoneName]):
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
        if not (zoneName in self._serversReservedResources):
            self._serversReservedResources[zoneName] = {}
        if not (serverID in self._serversReservedResources):
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
        if not (zoneName in self._serversReservedResources):
            self._serversReservedResources[zoneName] = {}
        if not (serverID in self._serversReservedResources):
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

    def getServerByIP(self, nodeIP, zoneName):
        for serverID, serverInfo in self._servers[zoneName].items():
            server = serverInfo['server']
            if (nodeIP.lower() == server.getControlNICIP().lower()) \
                    or (nodeIP.lower() == server.getDatapathNICIP().lower()):
                return server
        else:
            return None

    def getServersNumByZone(self, zoneName):
        return len(self._servers[zoneName])
