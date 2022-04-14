#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.xibMaintainer import *
from sam.base.socketConverter import SocketConverter, BCAST_MAC
from sam.base.loggerConfigurator import LoggerConfigurator


class DHCPServer(XInfoBaseMaintainer):
    def __init__(self):
        logConfigur = LoggerConfigurator(__name__, './log',
            'orchestrator.log', level='warning')
        self.logger = logConfigur.getLogger()

        self._sc = SocketConverter()
        self._ipMappingTable = {}    # TODO
        self._assignedIPPool = {}    # [switchID] = []

    def assignIP(self, switchID):
        if not self._assignedIPPool.has_key(switchID):
            self.logger.debug("New switchID:{0}".format(switchID))
            self._assignedIPPool[switchID] = []

        lanNet = self.genLanNet(switchID)

        minIP = self._getMinIP(lanNet)
        maxIP = self._getMaxIP(lanNet)
        self.logger.debug("minIP:{0}, maxIP:{1}".format(
            self._sc.int2ip(minIP), self._sc.int2ip(maxIP)))

        # if self._assignedIPPool[switchID] != []:
        #     potentialIP = self._assignedIPPool[switchID][-1] + 1
        #     if (potentialIP in range(minIP + 3, maxIP, 1)
        #             and potentialIP not in self._assignedIPPool[switchID]):
        #         self._assignedIPPool[switchID].append(potentialIP)
        #         return self._sc.int2ip(potentialIP)

        for ip in range(minIP + 3, maxIP, 1): # exclude lanNet, gateway, classifier and broadcast
            if ip not in self._assignedIPPool[switchID]:
                self._assignedIPPool[switchID].append(ip)
                return self._sc.int2ip(ip)
        else:
            raise ValueError("can't assign ip address")

    def assignClassifierIP(self, switchID):
        if not self._assignedIPPool.has_key(switchID):
            self.logger.debug("New switchID:{0}".format(switchID))
            self._assignedIPPool[switchID] = []

        lanNet = self.genLanNet(switchID)

        minIP = self._getMinIP(lanNet)
        ip = minIP + 2
        if not ip in self._assignedIPPool[switchID]:
            self._assignedIPPool[switchID].append(ip)
            return self._sc.int2ip(ip)
        else:
            self.logIPPool(switchID)
            raise ValueError("can't assign classifier ip address for server connect to switchID: {0}".format(
                switchID))

    def logIPPool(self, switchID):
        self.logger.debug("switchID {0}'s ip pools:".format(switchID))
        for ip in self._assignedIPPool[switchID]:
            self.logger.debug("ip: {0}".format(self._sc.int2ip(ip)))

    def _getMinIP(self, lanNet):
        ipv4 = lanNet.split("/")[0]
        ipv4Int = self._sc.ip2int(ipv4)
        return ipv4Int

    def _getMaxIP(self, lanNet):
        ipv4 = lanNet.split("/")[0]
        prefixLen = int(lanNet.split("/")[1])
        self.logger.debug("prefixLen:{0}".format(prefixLen))
        mask = (0xFFFFFFFF00000000 >> prefixLen) & 0xFFFFFFFF
        self.logger.debug("mask:{0}, ~mask:{1}".format(
            self._sc.int2ip(mask), self._sc.int2ip(~mask & 0xFFFFFFFF)))
        ipv4Int = self._sc.ip2int(ipv4) & mask
        return ipv4Int | (~mask & 0xFFFFFFFF)

    def genLanNet(self, switchID):
        third = (switchID & 0x7F8) >> 3
        fourth = (switchID & 0x7) << 5
        prefix = "2.2." + str(third) + "." + str(fourth) + "/27"
        self.logger.debug("genLanNet switchID:{0}, prefix:{1}".format(switchID, prefix))
        return prefix
