#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.vnf import NAME_OF_VNFTYPE


class NF(object):
    def __init__(self, nf, pkt, flow_count):
        assert isinstance(pkt, int)
        assert isinstance(flow_count, int)
        self.nf = NAME_OF_VNFTYPE[nf]
        self.pkt = pkt
        self.flow_count = flow_count

    def __str__(self):
        return '%s %d %d' % (self.nf, self.pkt, self.flow_count)
