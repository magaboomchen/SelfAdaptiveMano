#!/usr/bin/python
# -*- coding: UTF-8 -*-

LINK_DEFAULT_BANDWIDTH = 1   # Gbps


class Link(object):
    def __init__(self, srcID, dstID, 
            bandwidth=LINK_DEFAULT_BANDWIDTH,
            linkLength=1, 
            utilization=0):
        self.srcID = srcID  # link的起始端点交换机的switchID
        self.dstID = dstID  # link的终止端点交换机的switchID
        self.linkLength = linkLength    # unit: meter
        self.bandwidth = bandwidth
        self.utilization = utilization  # 链路带宽利用率

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)
