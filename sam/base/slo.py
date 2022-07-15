#!/usr/bin/python
# -*- coding: UTF-8 -*-


class SLO(object):
    def __init__(self, availability=None, latency=None, 
            throughput=None, dropRate=None, connections=None):
        self.availability = availability    # unit: %
        self.latency = latency              # unit: ms
        self.throughput = throughput        # unit: Gbps
        self.dropRate = dropRate            # unit: %
        self.connections = connections      # unit: ~
