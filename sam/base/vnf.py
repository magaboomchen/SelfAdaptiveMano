#!/usr/bin/python
# -*- coding: UTF-8 -*-

VNF_TYPE_CLASSIFIER = 0
VNF_TYPE_FORWARD = 1
VNF_TYPE_FW = 2
VNF_TYPE_IDS = 3
VNF_TYPE_MONITOR = 4
VNF_TYPE_LB = 5
VNF_TYPE_TRAFFICSHAPER = 6
VNF_TYPE_NAT = 7
VNF_TYPE_VPN = 8

VNFID_LENGTH = 4 # DO NOT MODIFY THIS VALUE, otherwise BESS will incurr error


class VNFIStatus(object):
    def __init__(self):
        self.inputTrafficAmount = None
        self.inputPacketAmount = None
        self.outputTrafficAmount = None
        self.outputPacketAmount = None


class VNFI(object):
    def __init__(self, vnfID=None, vnfType=None, vnfiID=None,
        config=None, node=None, vnfiStatus=None):
        self.vnfID = vnfID
        self.vnfType = vnfType
        self.vnfiID = vnfiID
        self.config = config
        self.node = node # server or switch
        self.vnfiStatus = vnfiStatus
        self.minCPUNum = 1
        self.maxCPUNum = 2
        self.minMem = 1024
        self.maxMem = 1024

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)


class VNFIRequest(object):
    def __init__(self, userID, requestID, requestType, vnfiID, config=None):
        self.userID =  userID # 0 is root
        self.requestID = requestID # uuid1()
        self.requestType = requestType # GETCONFIG/UPDATECONFIG/GETVNFI
        self.vnfiID = vnfiID
        self.config = config

