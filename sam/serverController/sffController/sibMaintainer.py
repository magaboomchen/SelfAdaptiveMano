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
        self._sfcSet = {}   # {sfcUUID:[sfciid]}

    def addLogger(self, logger):
        self.logger = logger

    def getModuleNameSuffix(self,VNFIID,directionID):
        return "_" + str(VNFIID) + "_" + str(directionID)

    def getModuleName(self,mclass,VNFIID,directionID):
        return str(mclass) + self.getModuleNameSuffix(VNFIID,directionID)

    def getVdev(self,VNFIID,directionID):
        suffix = self.getModuleNameSuffix(VNFIID,directionID)
        return  "net_vhost" + suffix + ",iface=/tmp/vsock" + suffix

    def getNextVNFID(self,sfci,vnf,directionID):
        VNFISequence = copy.deepcopy(sfci.VNFISequence)
        if directionID == 0:
            pass
        elif directionID == 1:
            VNFISequence.reverse()
        else:
            raise ValueError('Invalid direction ID.')

        sfcLen = len(VNFISequence)
        VNFID = vnf.VNFID
        for i in range(sfcLen):
            currentVNF = VNFISequence[i][0]
            if currentVNF.VNFID == VNFID:
                if i != (sfcLen-1):
                    return VNFISequence[i+1][0].VNFID
                else:
                    return VNF_TYPE_CLASSIFIER

    def getUpdateValue(self,SFCIID,nextVNFID):
        value = ((SFCIID & 0xFFF) << 4) + (nextVNFID & 0XF)
        return value

    def assignSFFWM2OGate(self,VNFID,directionID):
        OGateList = self.getModuleOGateNumList("wm2")
        oGateNum = self.genAvailableMiniNum4List(OGateList)
        self.addOGate2Module("wm2",(VNFID,directionID),oGateNum)
        return oGateNum

    def getSFFWM2MatchValue(self,SFCIID,VNFID,directionID):
        value = (10<<24) + ((SFCIID & 0xFFF) << 12) + ((VNFID & 0XF)<<8) + ((directionID & 0x1) <<7)
        return value
    
    def show(self):
        self.logger.info("sfcSet:{0}".format(self._sfcSet))
        self.logger.info("modules:{0}".format(self._modules))
        self.logger.info("links:{0}".format(self._links))

