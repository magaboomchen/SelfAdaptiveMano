#!/usr/bin/python
# -*- coding: UTF-8 -*-

import copy

from sam.base.server import Server
from sam.base.messageAgent import *
from sam.base.sfc import *
from sam.base.command import *
from sam.base.path import *
from sam.serverController.bessInfoBaseMaintainer import *

# TODO: need test


class SIBMS(object):
    def __init__(self, logger):
        self._sibms = {} # {serverID:SIBMaintainer}
        self.logger = logger

    def hasSibm(self, serverID):
        return self._sibms.has_key(serverID)

    def addSibm(self,serverID):
        self._sibms[serverID] = SIBMaintainer()
        self._sibms[serverID].addLogger(self.logger)

    def getSibm(self, serverID):
        return self._sibms[serverID]

    def delSibm(self,serverID):
        if serverID in self._sibms.iterkeys():
            del self._sibms[serverID]

    def show(self):
        for key in self._sibms.iterkeys():
            self.logger.info("{0}'s sibm:".format(key))
            self._sibms[key].show()


class SIBMaintainer(BessInfoBaseMaintainer):
    '''SFF Information Base Maintainer'''
    def __init__(self, *args, **kwargs):
        super(SIBMaintainer, self).__init__(*args, **kwargs)
        self._sfcSet = {}   # {sfcUUID:[sfciID]}
        self._vnfiDict = {} # {vnfiID:vnfi}

    def addLogger(self, logger):
        self.logger = logger

    def getModuleNameSuffix(self, vnfiID, directionID):
        return "_" + str(vnfiID) + "_" + str(directionID)

    def getModuleName(self, mclass, vnfiID, directionID):
        return str(mclass) + self.getModuleNameSuffix(vnfiID,directionID)

    def getVdev(self, vnfiID, directionID):
        suffix = self.getModuleNameSuffix(vnfiID,directionID)
        return  "net_vhost" + suffix + ",iface=/tmp/vsock" + suffix

    def getNextVNFID(self, sfci, vnf, directionID):
        vnfiSequence = copy.deepcopy(sfci.vnfiSequence)
        if directionID == 0:
            pass
        elif directionID == 1:
            vnfiSequence.reverse()
        else:
            raise ValueError('Invalid direction ID.')

        sfcLen = len(vnfiSequence)
        vnfID = vnf.vnfID
        for i in range(sfcLen):
            currentVNF = vnfiSequence[i][0]
            if currentVNF.vnfID == vnfID:
                if i != (sfcLen-1):
                    return vnfiSequence[i+1][0].vnfID
                else:
                    return VNF_TYPE_CLASSIFIER

    def getUpdateValue(self, sfciID, nextVNFID):
        value = ((nextVNFID & 0XF) << 12) + (sfciID & 0xFFF)
        return value

    def assignSFFWM2OGate(self, vnfID, directionID):
        if self.hasModuleOGate("wm2", (vnfID,directionID)):
            oGateNum = self.getModuleOGate("wm2", (vnfID,directionID))
        else:
            OGateList = self.getModuleOGateNumList("wm2")
            oGateNum = self.genAvailableMiniNum4List(OGateList)
            self.addOGate2Module("wm2", (vnfID,directionID), oGateNum)
        return oGateNum

    def getSFFWM2MatchValue(self, sfciID, vnfID, directionID):
        value = (10<<24) + ((vnfID & 0XF)<<20) \
                + ((sfciID & 0xFFF) << 8) + ((directionID & 0x1) <<7)
        return value

    def show(self):
        self.logger.info("sfcSet:{0}".format(self._sfcSet))
        self.logger.info("modules:{0}".format(self._modules))
        self.logger.info("links:{0}".format(self._links))

    def hasVNFI(self, vnfiID):
        return self._vnfiDict.has_key(vnfiID)

    def addVNFI(self, vnfi):
        self._vnfiDict[vnfi.vnfiID] = vnfi

    def delVNFI(self, vnfiID):
        self._vnfiDict.pop(vnfiID, None)
