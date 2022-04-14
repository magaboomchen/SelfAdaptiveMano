#!/usr/bin/python
# -*- coding: UTF-8 -*-

from __future__ import print_function

from sam.serverController.bessInfoBaseMaintainer import BessInfoBaseMaintainer

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
        self._sfcSet = {}   # {sfcUUID:[sfciID]}

    def addSFCDirection(self,sfcUUID,directionID):
        self._sfcSet[(sfcUUID,directionID)] = []

    def delSFCDirection(self,sfcUUID,directionID):
        del self._sfcSet[(sfcUUID,directionID)]

    def addSFCIDirection(self,sfcUUID,directionID,sfciID):
        self._sfcSet[(sfcUUID,directionID)].append(sfciID)

    def delSFCIDirection(self,sfcUUID,directionID,sfciID):
        self._sfcSet[(sfcUUID,directionID)].remove(sfciID)

    def canDeleteSFCDirection(self,sfcUUID,directionID):
        return self._sfcSet[(sfcUUID,directionID)] == []

    def hasSFCDirection(self,sfcUUID,direction):
        return self._sfcSet.has_key((sfcUUID,direction))

    def assignHashLBOGatesList(self,serverID,sfcUUID,direction,sfciID):
        hashLBName = self.getHashLBName(sfcUUID,direction)
        OGateList = self.getModuleOGateNumList(hashLBName)
        oGateNum = self.genAvailableMiniNum4List(OGateList)
        self.addOGate2Module(hashLBName,sfciID,oGateNum)
        OGateList.append(oGateNum)
        return OGateList

    def getHashLBName(self,sfcUUID,direction):
        mclass = "HashLB"
        moduleNameSuffix = '_' + str(sfcUUID) + '_' + str(direction['ID'])
        return mclass + moduleNameSuffix

    def getSFCSet(self):
        return self._sfcSet
