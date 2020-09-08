#!/usr/bin/python
# -*- coding: UTF-8 -*-

from __future__ import print_function
import uuid

from sam.base.server import Server
from sam.base.messageAgent import *
from sam.base.sfc import *
from sam.base.command import *
from sam.base.path import *
from sam.serverController.bessInfoBaseMaintainer import *

# TODO: need test

class CIBMS(object):
    def __init__(self):
        self._cibms = {} # {serverID:CIBMaintainer}

    def hasCibm(self, serverID):
        return self._cibms.has_key(serverID)

    def addCibm(self,serverID):
        self._cibms[serverID] = CIBMaintainer()

    def getCibm(self, serverID):
        return self._cibms[serverID]

class CIBMaintainer(BessInfoBaseMaintainer):
    '''Classifiers Information Base Maintainer'''
    def __init__(self, *args, **kwargs):
        super(CIBMaintainer, self).__init__(*args, **kwargs)
        self._sfcSet = {}   # {sfcUUID:[sfciid]}

    def addSFCDirection(self,sfcUUID,directionID):
        self._sfcSet[(sfcUUID,directionID)] = []

    def delSFCDirection(self,sfcUUID,directionID):
        del self._sfcSet[(sfcUUID,directionID)]

    def addSFCIDirection(self,sfcUUID,directionID,SFCIID):
        self._sfcSet[(sfcUUID,directionID)].append(SFCIID)

    def delSFCIDirection(self,sfcUUID,directionID,SFCIID):
        self._sfcSet[(sfcUUID,directionID)].remove(SFCIID)

    def canDeleteSFCDirection(self,sfcUUID,directionID):
        return self._sfcSet[(sfcUUID,directionID)] == []

    def hasSFCDirection(self,sfcUUID,direction):
        return self._sfcSet.has_key((sfcUUID,direction))

    def assignHashLBOGatesList(self,serverID,sfcUUID,direction,SFCIID):
        hashLBName = self.getHashLBName(sfcUUID,direction)
        OGateList = self.getModuleOGateNumList(hashLBName)
        oGateNum = self.genAvailableMiniNum4List(OGateList)
        self.addOGate2Module(hashLBName,SFCIID,oGateNum)
        OGateList.append(oGateNum)
        return OGateList

    def getHashLBName(self,sfcUUID,direction):
        mclass = "HashLB"
        moduleNameSuffix = '_' + str(sfcUUID) + '_' + str(direction['ID'])
        return mclass + moduleNameSuffix