#!/usr/bin/python
# -*- coding: UTF-8 -*-

VNF_TYPE_CLASSIFIER = 0
VNF_TYPE_FORWARD = 1
VNF_TYPE_FW = 2
VNF_TYPE_IDS = 3
VNF_TYPE_MONITOR = 4
VNF_TYPE_LB = 5
VNF_TYPE_TRAFFICSHAPER = 6

VNFID_LENGTH = 4 # DO NOT MODIFY THIS VALUE, otherwise BESS will incurr error

class VNFIStatus(object):
    def __init__(self):
        self.inputTrafficAmount = None
        self.inputPacketAmount = None
        self.outputTrafficAmount = None
        self.outputPacketAmount = None


class VNFI(object):
    def __init__(self, VNFID=None, VNFType=None, VNFIID=None,
        config=None, node=None, vnfiStatus=None):
        self.VNFID = VNFID
        self.VNFType = VNFType
        self.VNFIID = VNFIID
        self.config = config
        self.node = node # server or switch
        self.vnfiStatus = vnfiStatus
        self.minCPUNum = 2
        self.maxCPUNum = 2
        self.minMem = 1024
        self.maxMem = 1024


class VNFIRequest(object):
    def __init__(self, userID, requestID, requestType, VNFIID, config=None):
        self.userID =  userID # 0 is root
        self.requestID = requestID # uuid1()
        self.requestType = requestType # GETCONFIG/UPDATECONFIG/GETVNFI
        self.VNFIID = VNFIID
        self.config = config
