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
        self._hosts = {}
        self._vnfis = {}

    def updateServers(self, servers):
        self._servers = servers

    def updateSwitches(self, switches):
        self._switches = switches

    def updateLinks(self, links):
        self._links = links

    def updateHosts(self, hosts):
        self._hosts = hosts

    def updateVnfis(self, vnfis):
        self._vnfis = vnfis
    
    def getServers(self):
        return self._servers
    
    def getSwitches(self):
        return self._switches

    def getLinks(self):
        return self._links
    
    def getHosts(self):
        return self._hosts
    
    def getVnfis(self):
        return self._vnfis

