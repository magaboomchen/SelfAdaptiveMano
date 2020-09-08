#!/usr/bin/python
# -*- coding: UTF-8 -*-

class XInfoBaseMaintainer(object):
    def __init__(self):
        pass

    def genAvailableMiniNum4List(self,numList):
        if numList == []:
            return 0
        numList.sort()
        maxNum = max(numList)
        minNum = min(numList)
        if minNum != 0:
            return 0
        for i in range(len(numList)-1):
            currentNum = numList[i]
            nextNum = numList[i+1]
            if nextNum-currentNum > 1:
                return currentNum + 1
        else:
            return maxNum+1