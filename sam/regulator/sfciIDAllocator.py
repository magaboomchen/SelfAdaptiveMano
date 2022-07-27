#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.sfc import STATE_DELETED, STATE_INIT_FAILED
from sam.serverController.vnfController.sourceAllocator import SourceAllocator


class SFCIDAllocator(SourceAllocator):
    def __init__(self, oib, start, maxNum):
        self._oib = oib
        self.start = start
        self._maxNum = maxNum
        self._unallocatedList = [[self.start, self._maxNum]]  # simple implementation

    def allocateSFCID(self):
        return self.allocateSource(1)
    
    def allocateSpecificSFCID(self, sfciID):
        return self.allocateSpecificSource(sfciID, 1)

    def freeSFCID(self, sfciID):
        return self.freeSource(sfciID, 1)

    def getDeletedStateSFCIID(self, sfc):
        # get deleted sfci for this sfc
        sfciIDList = self._oib.getSFCCorrespondingSFCIID4DB(sfc.sfcUUID)
        for sfciID in sfciIDList:
            sfciState = self._oib.getSFCIState(sfciID)
            if sfciState == STATE_DELETED:
                self._oib.updateSFCIState(STATE_INIT_FAILED) 
                return sfciID
        return None

    def getAvaSFCIID(self):
        return self.allocateSFCID()
