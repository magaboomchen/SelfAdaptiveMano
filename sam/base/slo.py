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

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string