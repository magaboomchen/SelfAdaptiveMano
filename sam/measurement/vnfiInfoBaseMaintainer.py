#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os

from sam.base.server import *
from sam.base.link import *
from sam.base.xibMaintainer import XInfoBaseMaintainer
from sam.base.socketConverter import SocketConverter


class VNFIInfoBaseMaintainer(XInfoBaseMaintainer):
    def __init__(self):
        super(VNFIInfoBaseMaintainer, self).__init__()
        self._vnfis = {}
        self._vnfisReservedResources = {}
        self._sc = SocketConverter()

    def updateVnfisInAllZone(self, vnfis):
        self._vnfis = vnfis

    def updateVnfisByZone(self, vnfis, zoneName):
        self._vnfis[zoneName] = vnfis

    def getVnfisInAllZone(self):
        return self._vnfis

    def getVnfisByZone(self, zoneName):
        return self._vnfis[zoneName]
