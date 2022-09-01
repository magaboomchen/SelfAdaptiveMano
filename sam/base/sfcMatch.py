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
        return dict(
            (key, value)
            for (key, value) in self.__dict__.items()
            if value != None
            )

    def fromDict(self, dictionary):
        for key in list(self.__dict__.keys()):
            if key in dictionary:
                self.__dict__[key] = dictionary[key]
