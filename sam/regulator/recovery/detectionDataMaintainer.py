#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
    detectionDict = {
        "failure":{
            "switchIDList":[],
            "serverIDList":[],
            "linkIDList":[]
        },
        "abnormal":{
            "switchIDList":[],
            "serverIDList":[],
            "linkIDList":[]
        },
        "resume":{
            "switchIDList":[],
            "serverIDList":[],
            "linkIDList":[]
        }
    }
    allZoneDetectionDict={SIMULATOR_ZONE: detectionDict}
'''

from typing import Dict, Union

from sam.base.messageAgent import SIMULATOR_ZONE, TURBONET_ZONE


class DetectionDataMaintainer(object):
    def __init__(self):
        self.allZoneDetectionDict = {}  # type: Union[str, Dict]

    def addDetectionDict(self, allZoneDetectionDict):
        for zoneName, detectionDict in allZoneDetectionDict.items():
            if zoneName not in self.allZoneDetectionDict.keys():
                self.allZoneDetectionDict[zoneName] = detectionDict
            for detectionType, dataListDict in detectionDict.items():
                if detectionType not in detectionDict.keys():
                    self.allZoneDetectionDict[zoneName][detectionType] = dataListDict
                for dataListType, dataList in dataListDict.items():
                    if dataListType not in detectionDict.keys():
                        self.allZoneDetectionDict[zoneName][detectionType][dataListType] = dataList
                    for data in dataList:
                        if data not in self.allZoneDetectionDict[zoneName][detectionType][dataListType]:
                            self.allZoneDetectionDict[zoneName][detectionType][dataListType].append(data)

    def processResumeData(self, allZoneDetectionDict):
        for zoneName, detectionDict in allZoneDetectionDict.items():
            for detectionType, dataListDict in detectionDict.items():
                for dataListType, dataList in dataListDict.items():
                    for data in dataList:
                        self.allZoneDetectionDict[zoneName][detectionType][dataListType].remove(data)

    def getAllZoneDetectionDict(self):
        return self.allZoneDetectionDict

    def deleteDuplicateData(self, allZoneDetectionDict):
        for zoneName, detectionDict in allZoneDetectionDict.items():
            for detectionType, dataListDict in detectionDict.items():
                for dataListType in list(dataListDict.keys()):
                    dataList = allZoneDetectionDict[zoneName][detectionType][dataListType]
                    allZoneDetectionDict[zoneName][detectionType][dataListType] = list(set(dataList))
        return allZoneDetectionDict
