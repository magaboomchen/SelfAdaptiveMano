#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.xibMaintainer import XInfoBaseMaintainer


class SFCIInfoBaseMaintainer(XInfoBaseMaintainer):
    def __init__(self):
        super(SFCIInfoBaseMaintainer, self).__init__()
        self._sfcis = {}
        self._sfcisReservedResources = {}

    def updateSFCIsInAllZone(self, sfcis):
        self._sfcis = sfcis

    def updateSFCIsByZone(self, sfcis, zoneName):
        self._sfcis[zoneName] = sfcis

    def getSFCIsInAllZone(self):
        return self._sfcis

    def getSFCIsByZone(self, zoneName):
        return self._sfcis[zoneName]
