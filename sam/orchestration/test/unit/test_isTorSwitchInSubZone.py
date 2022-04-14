#!/usr/bin/python
# -*- coding: UTF-8 -*-

class test(object):
    def __init__(self):
        self.podNum = 4
        self.minPodIdx = 1
        self.maxPodIdx = 3

    def isTorSwitchInSubZone(self, switchID):
        # self.podNum 
        # self.minPodIdx
        # self.maxPodIdx

        coreSwitchNum = pow(self.podNum/2,2)
        aggrSwitchNum = self.podNum/2*self.podNum
        torSwitchNum = self.podNum/2*self.podNum
        torSwitchStartIdx = coreSwitchNum + aggrSwitchNum
        torSwitchEndIdx = torSwitchStartIdx + torSwitchNum - 1
        torPerPod = self.podNum/2

        subZoneTorSwitchStartIdx = torSwitchStartIdx + self.minPodIdx * torPerPod
        subZoneTorSwitchEndIdx = subZoneTorSwitchStartIdx + (self.maxPodIdx - self.minPodIdx + 1) * torPerPod - 1

        if switchID >= subZoneTorSwitchStartIdx and switchID <= subZoneTorSwitchEndIdx:
            return True
        else:
            return False

if __name__ == "__main__":
    t = test()
    for switchID in range(20):
        a = t.isTorSwitchInSubZone(switchID)
        print(a)