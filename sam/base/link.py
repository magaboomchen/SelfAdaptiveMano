#!/usr/bin/python
# -*- coding: UTF-8 -*-

LINK_DEFAULT_BANDWIDTH = 1   # unit: Gbps


class Link(object):
    def __init__(self, srcID,   # type: int
            dstID,              # type: int 
            bandwidth=LINK_DEFAULT_BANDWIDTH,   # type: int
            linkLength=1,   # type: int
            utilization=0,  # type: float
            queueLatency=0,     # type: int 
            queueBufferUsage=0,         # type: int 
            queueBufferCapacity=0,      # type: int 
            NSH_num=0,          # type: int
            SYN_num=0,          # type: int
            DNS_num=0,          # type: int
            last_timestamp=0,   # type: int
            this_timestamp=0    # type: int
            ):
        self.srcID = srcID  # link's start point nodeID
        self.dstID = dstID  # link's end point nodeID
        self.linkLength = linkLength    # length of link wire, unit: meter
        self.bandwidth = bandwidth      # physical bandwidth capacity, unit: GBps
        self.utilization = utilization  # link bandwidth utilization, 0 < utilization < 1
        self.queueBufferUsage = queueBufferUsage        # the buffer usage, unit: MB
        self.queueBufferCapacity = queueBufferCapacity  # the buffer capacity, unit: MB
        self.queueLatency = queueLatency    # queue latency of this link, unit: nanoseconds
        self.NSH_num=NSH_num        # NSH packet counter, unit: None
        self.SYN_num=SYN_num        # SYN packet counter, unit: None
        self.DNS_num=DNS_num        # DNS packet counter, unit: None
        self.last_timestamp=last_timestamp  # timestamp of the last probe arriving at this link, unit: nanoseconds
        self.this_timestamp=this_timestamp  # timestamp of the current probe arriving at this link, unit: nanoseconds

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)
