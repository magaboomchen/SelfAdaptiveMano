#!/usr/bin/python
# -*- coding: UTF-8 -*-


class SLO(object):
    def __init__(self, availability=None, latencyBound=None, 
            throughput=None, dropRate=None, connections=None, latency=None):
        self.availability = availability    # unit: %
        self.latencyBound = latencyBound    # unit: ms
        self.latency = latency              # unit: ms
        self.throughput = throughput        # unit: Gbps
        self.dropRate = dropRate            # unit: %
        self.connections = connections      # unit: ~
