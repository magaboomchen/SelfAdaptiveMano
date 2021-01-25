#!/usr/bin/python
# -*- coding: UTF-8 -*-

import copy


class FRRPathIDAllocator(object):
    def __init__(self, requestList):
        self._requestList = requestList
        self._pathIDDict = {}
        self._startPathID = 2

    def genPathID(self, rIndex, failureElementID):
        if rIndex not in self._pathIDDict.keys():
            self._pathIDDict[rIndex] = {}
            self._pathIDDict[rIndex][failureElementID] = self._startPathID
        else:
            if failureElementID not in self._pathIDDict[rIndex].keys():
                newPathID = self._startPathID + len(self._pathIDDict[rIndex])
                self._pathIDDict[rIndex][failureElementID] = newPathID
        
        return self._pathIDDict[rIndex][failureElementID]
