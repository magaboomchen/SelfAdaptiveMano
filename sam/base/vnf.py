#!/usr/bin/python
# -*- coding: UTF-8 -*-

from typing import Union

from sam.base.acl import ACLTable
from sam.base.monitorStatistic import MonitorStatistics
from sam.base.rateLimiter import RateLimiterConfig
from sam.base.server import Server
from sam.base.switch import Switch

VNF_TYPE_CLASSIFIER = 0
VNF_TYPE_FORWARD = 1
VNF_TYPE_FW = 2
VNF_TYPE_IDS = 3
VNF_TYPE_MONITOR = 4
VNF_TYPE_LB = 5
VNF_TYPE_RATELIMITER = 6
VNF_TYPE_NAT = 7
VNF_TYPE_VPN = 8
VNF_TYPE_WOC = 9  # WAN Optimization Controller
VNF_TYPE_APPFW = 10  # http firewall
VNF_TYPE_VOC = 11
VNF_TYPE_DDOS_SCRUBBER = 12
VNF_TYPE_FW_RECEIVER = 13  # duplicate firewall in sfc
VNF_TYPE_NAT_RECEIVER = 14  # duplicate nat in sfc
# vnf type can't exceed 16, i.e. vnf type < 16
VNF_TYPE_MAX = 15

VNFID_LENGTH = 4  # DO NOT MODIFY THIS VALUE, otherwise BESS will incurr error

NAME_OF_VNFTYPE = {
    VNF_TYPE_FORWARD: 'VNF_TYPE_FORWARD',
    VNF_TYPE_FW: 'VNF_TYPE_FW',
    VNF_TYPE_IDS: 'VNF_TYPE_IDS',
    VNF_TYPE_MONITOR: 'VNF_TYPE_MONITOR',
    VNF_TYPE_LB: 'VNF_TYPE_LB',
    VNF_TYPE_RATELIMITER: 'VNF_TYPE_RATELIMITER',
    VNF_TYPE_NAT: 'VNF_TYPE_NAT',
    VNF_TYPE_VPN: 'VNF_TYPE_VPN',
    VNF_TYPE_WOC: 'VNF_TYPE_WOC',
    VNF_TYPE_APPFW: 'VNF_TYPE_APPFW',
    VNF_TYPE_VOC: 'VNF_TYPE_VOC',
    VNF_TYPE_DDOS_SCRUBBER: 'VNF_TYPE_DDOS_SCRUBBER',
    VNF_TYPE_FW_RECEIVER: 'VNF_TYPE_FW_RECEIVER',
    VNF_TYPE_NAT_RECEIVER: 'VNF_TYPE_NAT_RECEIVER',
}

PREFERRED_DEVICE_TYPE_P4 = "DEVICE_TYPE_P4"
PREFERRED_DEVICE_TYPE_SERVER = "DEVICE_TYPE_SERVER"

VNFI_RESOURCE_QUOTA_SMALL = {
    "cpu": 1,
    "mem": 1,    # 1 GiB hugepage
    "fwRules": 100
}

VNFI_RESOURCE_QUOTA_MEDIUM = {
    "cpu": 4,
    "mem": 2,    # 2 GiB hugepage
    "fwRules": 200
}

VNFI_RESOURCE_QUOTA_LARGE = {
    "cpu": 8,
    "mem": 4,    # 4 GiB hugepage
    "fwRules": 400
}


class VNF(object):
    def __init__(self, vnfUUID=None, vnfType=None, config=None,
                 preferredDeviceType=None):
        self.vnfUUID = vnfUUID
        self.vnfType = vnfType
        self.config = config
        self.preferredDeviceType = preferredDeviceType

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key, values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)


class VNFI(object):
    def __init__(self, vnfID=None, vnfType=None, vnfiID=None,
                 config=None, node=None, vnfiStatus=None):
        self.vnfID = vnfID              # equal to the vnfType
        self.vnfType = vnfType
        self.vnfiID = vnfiID
        self.config = config
        self.node = node                # type: Union[Server, Switch]
        self.vnfiStatus = vnfiStatus    # type: VNFIStatus
        self.minCPUNum = 1
        self.maxCPUNum = 1  # CPU core number: 100%
        self.cpuCoreDistribution = []  # place vnfi on specific core
        # e.g. [1,2,3,4] allocates core 1,2,3,4 for this vnfi
        self.minMem = 1024
        self.maxMem = 1024  # unit: MB
        self.memNUMADistribution = []  # place memory on specific numa node
        # e.g. [2,2] allocates 2 huge page on numa0 and 2 hugepages on numa1

    def to_dict(self):
        if type(self.node) == Switch:
            nodeID = self.node.switchID
        elif type(self.node) == Server:
            nodeID = self.node.getServerID()
        else:
            raise ValueError("Unknown node type {0}".format(type(self.node)))

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
        for key, values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)


# class VNFIRequest(object):
#     def __init__(self, userID, requestID, requestType, vnfiID, config=None):
#         self.userID =  userID # 0 is root
#         self.requestID = requestID # uuid1()
#         self.requestType = requestType # GETCONFIG/UPDATECONFIG/GETVNFI
#         self.vnfiID = vnfiID
#         self.config = config


class VNFIStatus(object):
    def __init__(self, inputTrafficAmount=None, inputPacketAmount=None,
                 outputTrafficAmount=None, outputPacketAmount=None,
                 state=None):
        # type: (dict[int,int], dict[int,int], dict[int,int], dict[int,int], Union[MonitorStatistics, RateLimiterConfig, ACLTable]) -> None
        self.inputTrafficAmount = inputTrafficAmount  # dict[int, int]
        self.inputPacketAmount = inputPacketAmount
        self.outputTrafficAmount = outputTrafficAmount
        self.outputPacketAmount = outputPacketAmount
        self.state = state

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key, values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string
