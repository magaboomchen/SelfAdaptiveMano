#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging

class VIOAllocator(object):
    def __init__(self, serverID, maxVdevNum):
        self._serverID = serverID
        self._maxNum = maxVdevNum
        self._counter = 0
        # here use a set to indicate whether the port has been allocated.
        # TODO: maybe it is better to replace it with a bitmap (but bitmap in Python is not so efficient)
        self._allocatedSet = set()

    def allocateVIO(self):
        while self._counter < self._maxNum:
            if self._counter in self._allocatedSet:
                self._counter += 2
            else:
                self._allocatedSet.add(self._counter)
                self._counter += 2
                return self._counter - 2
        # if _counter >= self._maxNum
        if len(self._allocatedSet) * 2 >= self._maxNum:
            logging.error('Server %s: Allocated number of vio exceeds the limitation.' % self._serverID)
        self._counter = 0
        return self.allocateVIO()

    def freeVIO(self, start):
        try:
            self._allocatedSet.remove(start)
        except Exception as exp:
            pass   # ignore port not allocated
