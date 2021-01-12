#!/usr/bin/python
# -*- coding: UTF-8 -*-

SWITCH_TYPE_FORWARD = "SWITCH_TYPE_FORWARD" # 仅支持转发的交换机
SWITCH_TYPE_SFF = "SWITCH_TYPE_SFF" # 连接该交换机的服务器还支持部署VNF
SWITCH_TYPE_DCNGATEWAY = "SWITCH_TYPE_DCNGATEWAY"   # 数据中心网关

SWITCH_DEFAULT_TCAM_SIZE = 2000


class Switch(object):
    def __init__(self, switchID, switchType, lanNet=None, programmable=False,
        tcamSize=SWITCH_DEFAULT_TCAM_SIZE, tcamUsage=0):
        self.switchID = switchID    # 全网唯一标识
        self.switchType = switchType
        self.lanNet = lanNet    # 该交换机连接的服务器集群的IPv4网段
        self.programmable = programmable    # 该交换机是否支持可编程
        self.tcamSize = tcamSize    # 该交换机的TCAM容量
        self.tcamUsage = tcamUsage  # 该交换机的TCAM使用量
        self.supportNF = [] # 该交换机支持的NF列表，比如[NF_TYPE_FW]
        self.supportVNF = []    # 该交换机支持的VNF列表，比如[VNF_TYPE_FW]

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)
