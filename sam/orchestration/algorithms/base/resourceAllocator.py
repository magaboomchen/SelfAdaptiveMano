#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.orchestration.algorithms.base.mappingAlgorithmBase import MappingAlgorithmBase


class ResourceAllocator(MappingAlgorithmBase):
    def __init__(self, dib, zoneName):
        self._dib = dib
        self.zoneName = zoneName

    def allocate4UnaffectedForwardingPathSegDict(self,
                requestList, unaffectedForwardingPathSegDict):
        self.allocate4ForwardingPathDict(requestList,
                unaffectedForwardingPathSegDict)

    def allocate4ForwardingPathDict(self, requestList,
            forwardingPathDict):
        self.requestList = requestList
        iterLength = len(forwardingPathDict)
        for rIndex in range(iterLength):
            self.request = self.requestList[rIndex]
            forwardingPath = forwardingPathDict[rIndex]
            # forwardingPath: 
            # [[(0, 10018), (0, 13), (0, 5), (0, 3), (0, 9), (0, 17), (0, 10002)],
            # [(1, 10002), (1, 17), (1, 10002)], [(2, 10002), (2, 17), (2, 10002)],
            # [(3, 10002), (3, 17), (3, 8)]]
            self._allocateServerResource(forwardingPath)
            self._allocateSwitchResource(forwardingPath)
            self._allocateLinkResource(forwardingPath)
