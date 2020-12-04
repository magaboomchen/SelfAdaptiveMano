#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
Source (virtio ID or CPU) allocator for servers.
'''

import logging
from sam.serverController.vnfController.vcConfig import vcConfig
class SourceAllocator(object):
    def __init__(self, serverID, maxNum, start=0):
        self._serverID = serverID
        self._maxNum = maxNum
        self._unallocatedList = [[start, self._maxNum]]  # simple implementation

    def allocateSource(self, num):
        for i in range(len(self._unallocatedList)):
            if self._unallocatedList[i][1] - self._unallocatedList[i][0] > num:
                result = self._unallocatedList[i][0]
                self._unallocatedList[i][0] += num
                return result
            elif self._unallocatedList[i][1] - self._unallocatedList[i][0] == num:
                result = self._unallocatedList[i][0]
                del(self._unallocatedList[i])
                return result
        # no result found 
        return -1
    
    def freeSource(self, start, num):
        if len(self._unallocatedList) == 0:
            self._unallocatedList.append([start, start + num])
        if start + num <= self._unallocatedList[0][0]:
            self._unallocatedList.insert(0, [start, start + num])
        elif start >= self._unallocatedList[-1][1]:
            self._unallocatedList.append([start, start + num])
        else:
            for i in range(1, len(self._unallocatedList) - 1):
                if start >= self._unallocatedList[i - 1][1] and start + num <= self._unallocatedList[i][0]:
                    self._unallocatedList.insert(i, [start, start + num])
                    break
        # merge adjacent ranges
        for i in range(len(self._unallocatedList) - 1):
            if self._unallocatedList[i][1] == self._unallocatedList[i + 1][0]:
                self._unallocatedList[i][1] = self._unallocatedList[i + 1][1]
                del(self._unallocatedList[i + 1])
                break

def mapCpuCores(start, end):
    res = []
    for i in range(start, end + 1):
        if i * 2 < vcConfig.MAX_CPU_NUM:
            res.append(i * 2)
        else:
            res.append(2 * i - vcConfig.MAX_CPU_NUM + 1)
    resStr = ''
    for i in res:
        resStr = resStr + '%d,' % i
    resStr = resStr[:-1]
    return res, resStr

if __name__ == '__main__':
    print(mapCpuCores(1,2))
    print(mapCpuCores(5,7))