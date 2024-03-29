#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.xibMaintainer import XInfoBaseMaintainer

# TODO : test

class BessInfoBaseMaintainer(XInfoBaseMaintainer):
    def __init__(self, *args, **kwargs):
        super(BessInfoBaseMaintainer, self).__init__(*args, **kwargs)
        self._modules = {}
        self._links = {}

    def addModule(self,name,mclass):
        self._modules[name] = {'mclass':mclass,
            'rules':[],'ogates':{}}
        # 'ogates': {key:ogateNum}
        # key <- sfcUUID or SFCIID

    def delModule(self,name):
        if name in self._modules.keys():
            del self._modules[name]

    def getModule(self,name):
        if name in self._modules.keys():
            return self._modules[name]
        else:
            return None

    def getModuleOGateNumList(self,moduleName):
        ogates = self._modules[moduleName]['ogates']
        oGatesList = []
        for key, ogate in ogates.items():
            oGatesList.append(ogate)
        return oGatesList

    def addOGate2Module(self,moduleName,key,oGateNum):
        ogates = self._modules[moduleName]['ogates']
        ogates[key] = oGateNum

    def getModuleOGate(self,moduleName,key):
        ogates = self._modules[moduleName]['ogates']
        return ogates[key]

    def hasModuleOGate(self, moduleName, key):
        return key in self._modules[moduleName]['ogates']

    def delModuleOGate(self,moduleName,key):
        ogates = self._modules[moduleName]['ogates']
        del ogates[key]