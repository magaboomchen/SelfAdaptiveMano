#!/usr/bin/python
# -*- coding: UTF-8 -*-

from typing import Union

from sam.base.sfc import SFC
from sam.base.sfcConstant import STATE_DELETED, STATE_INIT_FAILED
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer
from sam.serverController.vnfController.sourceAllocator import SourceAllocator


class SFCIDAllocator(SourceAllocator):
    def __init__(self, oib, # type: OrchInfoBaseMaintainer
                start,      # type: int
                maxNum      # type: int
                ):
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

    def getDeletedOrInitFailedStateSFCIIDList(self, sfc):
        # type: (SFC) -> Union[int, None]
        # get deleted sfci for this sfc
        sfciIDList = self._oib.getSFCIIDListOfASFC4DB(sfc.sfcUUID)
        deledtedSFCIIDList = []
        for sfciID in sfciIDList:
            sfciState = self._oib.getSFCIState(sfciID)
            if sfciState in [STATE_DELETED, STATE_INIT_FAILED]:
                # self._oib.updateSFCIState(sfciID, STATE_INIT_FAILED) 
                deledtedSFCIIDList.append(sfciID)
        return deledtedSFCIIDList

    def getAvaSFCIID(self):
        return self.allocateSFCID()
