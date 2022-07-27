#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.vnf import VNFIStatus
from sam.base.xibMaintainer import XInfoBaseMaintainer


class SFCIInfoBaseMaintainer(XInfoBaseMaintainer):
    def __init__(self):
        super(SFCIInfoBaseMaintainer, self).__init__()
        self._sfcis = {}    # [sfciID]: sfci
        self._sfcisReservedResources = {}

    def updateSFCIsInAllZone(self, sfcis):
        self._sfcis = sfcis

    def updateSFCIsByZone(self, sfcis, zoneName):
        self._sfcis[zoneName] = sfcis

    def addSFCIByZone(self, sfci, zoneName):
        if zoneName not in self._sfcis:
            self._sfcis[zoneName] = {}
        self._sfcis[zoneName][sfci.sfciID] = sfci

    def delSFCIByZone(self, sfci, zoneName):
        if zoneName not in self._sfcis:
            self._sfcis[zoneName] = {}
        del self._sfcis[zoneName][sfci.sfciID]

    def updatePartialSFCIsByZone(self, sfcisDict, zoneName):
        if zoneName not in self._sfcis:
            self._sfcis[zoneName] = {}
        for sfciID, sfci in sfcisDict.items():
            if sfciID not in self._sfcis[zoneName]:
                self._sfcis[zoneName][sfciID] = sfci
            else:
                # vnfiSequence's vnfiStatus
                oldSFCI = self._sfcis[zoneName][sfciID]
                for vnfiSeqIdx,vnfis in enumerate(sfci.vnfiSequence):
                    for vnfiIdx,vnfi in enumerate(vnfis):
                        if type(vnfi.vnfiStatus) != VNFIStatus:
                            continue
                        else:
                            oldVNFI = oldSFCI.vnfiSequence[vnfiSeqIdx][vnfiIdx]
                            if type(oldVNFI.vnfiStatus) != VNFIStatus:
                                oldVNFI.vnfiStatus = VNFIStatus()
                            oldVNFIStatus = oldVNFI.vnfiStatus
                            newVNFIStatus = vnfi.vnfiStatus
                            self._updateVNFIStatus(oldVNFIStatus, newVNFIStatus)

                self._updateSFCISLO(oldSFCI)

                oldSFCI.forwardingPathSet = sfci.forwardingPathSet
                oldSFCI.routingMorphic = sfci.routingMorphic

    def _updateVNFIStatus(self, oldVNFIStatus, newVNFIStatus):
        if newVNFIStatus.inputTrafficAmount != None:
            oldVNFIStatus.inputTrafficAmount = newVNFIStatus.inputTrafficAmount
        if newVNFIStatus.inputPacketAmount != None:
            oldVNFIStatus.inputPacketAmount = newVNFIStatus.inputPacketAmount
        if newVNFIStatus.outputTrafficAmount != None:
            oldVNFIStatus.outputTrafficAmount = newVNFIStatus.outputTrafficAmount
        if newVNFIStatus.outputPacketAmount != None:
            oldVNFIStatus.outputPacketAmount = newVNFIStatus.outputPacketAmount
        if newVNFIStatus.state != None:
            oldVNFIStatus.state = newVNFIStatus.state

    def _updateSFCISLO(self, sfci):
        inputTrafficSum = self._getSFCIInputTrafficSum(sfci)
        outputTrafficSum = self._getSFCIOutputTrafficSum(sfci)
        sfci.sloRealTimeValue.throughput = outputTrafficSum
        sfci.sloRealTimeValue.dropRate = self._computeDropRate(inputTrafficSum, 
                                                                outputTrafficSum)

    def _getSFCIInputTrafficSum(self, sfci):
        inputTrafficSum = 0
        for vnfi in sfci.vnfiSequence[0]:
            if type(vnfi.vnfiStatus) == VNFIStatus:
                inputTrafficSum += vnfi.vnfiStatus.inputTrafficAmount
            else:
                inputTrafficSum += 0 
        return inputTrafficSum

    def _getSFCIOutputTrafficSum(self, sfci):
        outputTrafficSum = 0
        for vnfi in sfci.vnfiSequence[-1]:
            if type(vnfi.vnfiStatus) == VNFIStatus:
                outputTrafficSum += vnfi.vnfiStatus.outputTrafficAmount
            else:
                outputTrafficSum += 0
        return outputTrafficSum

    def _computeDropRate(self, inputTrafficSum, outputTrafficSum):
        if inputTrafficSum == 0:
            dropRate = 0
        else:
            dropRate = (inputTrafficSum - outputTrafficSum)/inputTrafficSum*100.0
        dropRate = min(dropRate, 100)
        dropRate = max(0, dropRate)
        return dropRate

    def getSFCIsInAllZone(self):
        return self._sfcis

    def getSFCIsByZone(self, zoneName):
        if zoneName in self._sfcis:
            return self._sfcis[zoneName]
        else:
            return {}
