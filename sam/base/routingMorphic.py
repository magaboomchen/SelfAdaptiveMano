#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
Caution: bits must be multiple of 8
'''

import numpy as np

from sam.base.socketConverter import SocketConverter, BCAST_MAC


class RoutingMorphic(object):
    def __init__(self):
        self._sc = SocketConverter()
        self.morphicName = None
        self.identifierName = None
        self.metadataDict = {}
        self.commonField = {}
        self.headerOffsets = None
        self.headerBits = None
        self.etherType = None
        self.ipProto = None

    def addMorphicName(self, morphicName):
        self.morphicName = morphicName

    def addIdentifierName(self, identifierName):
        self.identifierName = identifierName

    def getIdentifierDict(self):
        return self.metadataDict[self.identifierName]

    def addHeaderOffsets(self, headerOffsets):
        self.headerOffsets = headerOffsets

    def addHeaderBits(self, headerBits):
        self.headerBits = headerBits

    def addEtherType(self, etherType):
        self.etherType = etherType

    def addIPProto(self, ipProto):
        self.ipProto = ipProto

    def addNextHeaderProtocol(self, nextHeaderProtocol, offset, bits=8, dataType=np.uint8):
        self.commonField["nextHeaderProtocol"] = {
            "type": dataType,
            "offset": offset,
            "bits": bits,
            "value": nextHeaderProtocol
        }

    def addMetadata(self, metaDataName, dataType, offset, bits, value, humanReadable):
        self.metadataDict[metaDataName] = {
            "type": dataType,
            "offset": offset,
            "bits": bits,
            "value": value,
            "humanReadable": humanReadable
        }

    def delMetadata(self, metaDataName):
        del self.metadataDict[metaDataName]

    def from_dict(self, routingMorphicDictTemplate):
        self.addMorphicName(routingMorphicDictTemplate["morphicName"])
        self.addIdentifierName(routingMorphicDictTemplate["identifierName"])
        self.addHeaderOffsets(routingMorphicDictTemplate["headerOffsets"])
        self.addHeaderBits(routingMorphicDictTemplate["headerBits"])
        self.addEtherType(routingMorphicDictTemplate["etherType"])
        self.addIPProto(routingMorphicDictTemplate["ipProto"])
        nhpDict = routingMorphicDictTemplate["commonField"]["nextHeaderProtocol"]
        self.addNextHeaderProtocol(nhpDict["value"],
                                    nhpDict["offset"],
                                    nhpDict["bits"],
                                    nhpDict["type"]
                                    )
        for metadataName, metadataDict in routingMorphicDictTemplate["metadataDict"].items():
            self.addMetadata(metadataName, metadataDict["type"],
                                metadataDict["offset"],
                                metadataDict["bits"],
                                metadataDict["value"],
                                metadataDict["humanReadable"]
                                )

    def getMetadata(self, metaDataName):
        return self.metadataDict[metaDataName]

    def convertMatchFieldsDict(self, matchFiledsDict):
        matchOffsetBitsList = []
        for matchFieldName, value in matchFiledsDict.items():
            metaData = self.getMetadata(matchFieldName)
            matchOffsetBits = {
                "offset": metaData["offset"],
                "bits": metaData["bits"],
                "value": "{0:b}".format(value),
                "mask": self.bits2Mask(metaData["bits"])
            }
            matchOffsetBitsList.append(matchOffsetBits)
        return matchOffsetBitsList

    def bits2Mask(self, bitsLength):
        mask = 0x0
        for i in range(bitsLength):
            mask = mask + (0x1 << i)

        return self._sc.int2Bytes(mask, bitsLength/8)

    def encodeIdentifierForSFC(self, sfciID, vnfID):
        # sfci.sfciID, vnf.vnfID
        identifierDict = self.getIdentifierDict()
        identifierValue = identifierDict["value"]
        identifierType = identifierDict["type"]
        identifierBits = identifierDict["bits"]
        identifierBytes = identifierBits/8
        if identifierBits < 32 or identifierBits%8 != 0:
            raise ValueError("Invalid identifier bits")
        if self.morphicName == "IPv4":
            ipNum = (10<<24) + ((vnfID & 0xF) << 20) \
                        + ((sfciID & 0xFFF) << 8) \
                        + (0 & 0xFF)
            # return self._sc.int2ip(ipNum)
            
        else:
            sfciIDMask = self._sc.getFullMaskInHex(identifierBits/8 - 2)
            ipNum = (10<<(identifierBits-8)) + ((vnfID & 0xFF) << identifierBits-16) \
                        + (sfciID & sfciIDMask)
        return ipNum

    def decodeIdentifierDictForSFC(self, identifierDict):
        identifierValue = identifierDict["value"]
        identifierBits = identifierDict["bits"]
        if self.morphicName == "IPv4":
            vnfID = (identifierValue & 0x00F00000) >> 20
            sfciID = (identifierValue & 0x000FF00) >> 8
        elif self.morphicName == "IPv6":
            raise ValueError("Please implement this")
            # TODO
            vnfID = (identifierValue >> identifierBits-16) & 0xFF
            sfciIDMask = self._sc.getFullMaskInHex(identifierBits/8 - 2)
            sfciID = identifierValue & sfciIDMask
        else:
            vnfID = (identifierValue >> identifierBits-16) & 0xFF
            sfciIDMask = self._sc.getFullMaskInHex(identifierBits/8 - 2)
            sfciID = identifierValue & sfciIDMask
        return (sfciID, vnfID)

    def value2HumanReadable(self, identifierValue):
        if self.morphicName == "IPv4":
            return self._sc.int2ip(identifierValue)
        else:
            raise ValueError("please implement this function")
