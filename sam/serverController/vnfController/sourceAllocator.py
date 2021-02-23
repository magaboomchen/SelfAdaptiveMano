#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
Source (virtio ID or CPU) allocator for servers.
'''

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
    def __init__(self, serverID, coreInSocketList, notAvaiCPU=None):
        self._serverID = serverID
        coreInSocketList = self._rmNotAvaiCPUFromCoreInSocketList(coreInSocketList,
                                                                notAvaiCPU)
        self._coreInSocketList = coreInSocketList

    def _rmNotAvaiCPUFromCoreInSocketList(self, coreInSocketList, notAvaiCPU):
        # coreInSocketList example: [[0,2,4,6,8,10],[1,3,5,7,9,11]]
        for core in notAvaiCPU:
            for coreInSocket in coreInSocketList:
                if core in coreInSocket:
                    coreInSocket.remove(core)
                    break
        return coreInSocketList

    def allocateCPU(self, num):  # resCpu: [nodeIndex][] int
        resCpu = []
        for _ in self._coreInSocketList:
            resCpu.append([])

        for idx, coreInSocket in enumerate(self._coreInSocketList):
            if len(coreInSocket) >= num:
                resCpu[idx].extend(coreInSocket[:num])
                del(coreInSocket[:num])
                return resCpu

        for idx, coreInSocket in enumerate(self._coreInSocketList):  
            if num > len(coreInSocket):
                num -= len(coreInSocket)
                resCpu[idx].extend(coreInSocket)
                del(coreInSocket[:len(coreInSocket)])
            elif num <= len(coreInSocket):
                resCpu[idx].extend(coreInSocket[:num])
                del(coreInSocket[:num])
                return resCpu

        # not enough core 
        assert num > 0
        self.freeCPU(resCpu)
        return None, None 

    def freeCPU(self, cpus):
        for idx, each in enumerate(cpus):
            if len(each) > 0:
                self._coreInSocketList[idx].extend(cpus[idx])

    def getCPUList(self):
        return self._coreInSocketList


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