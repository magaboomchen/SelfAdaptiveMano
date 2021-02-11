#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.server import *
from sam.base.switch import *

VNF_TYPE_CLASSIFIER = 0
VNF_TYPE_FORWARD = 1
VNF_TYPE_FW = 2
VNF_TYPE_IDS = 3
VNF_TYPE_MONITOR = 4
VNF_TYPE_LB = 5
VNF_TYPE_RATELIMITER = 6
VNF_TYPE_NAT = 7
VNF_TYPE_VPN = 8
VNF_TYPE_WOC = 9    # WAN Optimization Controller
VNF_TYPE_APPFW = 10 # http firewall
VNF_TYPE_VOC = 11
VNF_TYPE_DDOS_SCRUBBER = 12
VNF_TYPE_FW_RECEIVER = 13   # duplicate firewall in sfc
VNF_TYPE_NAT_RECEIVER = 14  # duplicate nat in sfc
# vnf type can't exceed 16, i.e. vnf type < 16
VNF_TYPE_MAX = 15

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
        self.cpuCoreDistribution = []   # place vnfi on specific core
        # e.g. [1,2,3,4] allocates core 1,2,3,4 for this vnfi
        self.minMem = 1024
        self.maxMem = 1024
        self.memNUMADistribution = []   # place memory on specific numa node
        # e.g. [2,2] allocates 2 huge page on numa0 and 2 hugepages on numa1

    def to_dict(self):
        if type(self.node) == Switch:
            nodeID = self.node.switchID
        elif type(self.node) == Server:
            nodeID = self.node.getServerID()
        else:
            raise ValueError("Unknown node type {0}".format(type(node)))

        vnfDict = {
            "vnfType": self.vnfType,
            "vnfiID": self.vnfiID,
            "config": self.config,
            "nodeID": nodeID,
            "cpu": self.maxCPUNum,
            "memory": self.maxMem
        }

        return vnfDict

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
