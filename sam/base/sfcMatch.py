#!/usr/bin/python
# -*- coding: UTF-8 -*-


class SFCMatch(object):
    def __init__(self, srcIP='*', # type: str
                    dstIP='*',  # type: str
                    srcPort='*',    # type: str
                    dstPort='*',    # type: str
                    proto='*'    # type: str
                ):
        self.srcIP = srcIP
        self.dstIP = dstIP
        self.srcPort = srcPort
        self.dstPort = dstPort
        self.proto = proto

    def toDict(self):
        sfcMatchDict = {
            'srcIP': self.srcIP,
            'dstIP': self.dstIP,
            'srcPort': self.srcPort,
            'dstPort': self.dstPort,
            'proto': self.proto
        }
        return sfcMatchDict