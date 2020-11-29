#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.xibMaintainer import *

# TODO : test


class DCNInfoBaseMaintainer(XInfoBaseMaintainer):
    def __init__(self, *args, **kwargs):
        super(DCNInfoBaseMaintainer, self).__init__(*args, **kwargs)
        self._servers = {}
        self._switches = {}
        self._links = {}
        self._vnfis = {}
        # TODO: add reservation info for each elements, e.g. reserved cpu core for a server

    def updateServersInAllZone(self, servers):
        self._servers = servers

    def updateServersByZone(self, servers, zoneName):
        self._servers[zoneName] = servers

    def updateSwitchesInAllZone(self, switches):
        self._switches = switches

    def updateSwitchesByZone(self, switches, zoneName):
        self._switches[zoneName] = switches

    def updateLinksInAllZone(self, links):
        self._links = links

    def updateLinksByZone(self, links, zoneName):
        self._links[zoneName] = links

    def updateVnfisInAllZone(self, vnfis):
        self._vnfis = vnfis

    def updateVnfisByZone(self, vnfis, zoneName):
        self._vnfis[zoneName] = vnfis

    def getServersInAllZone(self):
        return self._servers

    def getServersByZone(self, zoneName):
        return self._servers[zoneName]

    def getSwitchesInAllZone(self):
        return self._switches

    def getSwitchesByZone(self, zoneName):
        return self._switches[zoneName]

    def getLinksInAllZone(self):
        return self._links

    def getLinksByZone(self, zoneName):
        return self._links[zoneName]

    def getVnfisInAllZone(self):
        return self._vnfis

    def getVnfisByZone(self, zoneName):
        return self._vnfis[zoneName]

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)

