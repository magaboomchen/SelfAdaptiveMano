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

class CPUAllocator(object):
    def __init__(self, serverID, cpuList, notAvaiCPU=None):  
        self._serverID = serverID
        
        for cpu in notAvaiCPU:
            for each in cpuList:
                if cpu in each:
                    each.remove(cpu)
                    break

        self._cpuList = cpuList
                    
    def allocateCPU(self, num):  # resCpu: [nodeNum][] int
        resCpu = []
        for _ in self._cpuList:
            resCpu.append([])

        for idx, each in enumerate(self._cpuList):
            if len(each) >= num:
                resCpu[idx].extend(each[:num])
                del(each[:num])
                return resCpu

        for idx, each in enumerate(self._cpuList):  
            if num > len(each):
                num -= len(each)
                resCpu[idx].extend(each)
                del(each[:len(each)])
            elif num <= len(each):
                resCpu[idx].extend(each[:num])
                del(each[:num])
                return resCpu
        
        # not enough cpu 
        assert num > 0
        self.freeCPU(resCpu)
        return None, None 

    def freeCPU(self, cpus):
        for idx, each in enumerate(cpus):
            if len(each) > 0:
                self._cpuList[idx].extend(cpus[idx])

    def getCPUList(self):
        return self._cpuList

if __name__ == '__main__':
    ''' test '''  
    cpuAllo = CPUAllocator(0, [[0,2,4,6],[1,3,5,7]], [0])
    print(cpuAllo.getCPUList())
    print(cpuAllo.allocateCPU(2))
    print(cpuAllo.getCPUList())
    print(cpuAllo.allocateCPU(2))
    print(cpuAllo.getCPUList())
    print(cpuAllo.allocateCPU(3))
    print(cpuAllo.getCPUList())