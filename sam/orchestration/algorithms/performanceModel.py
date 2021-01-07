#!/usr/bin/python
# -*- coding: UTF-8 -*-

import math

from sam.base.link import *

SPEED_OF_LIGHT = 3.0 * pow(10, 8)


class PerformanceModel(object):
    def __init__(self):
        self.alpha = 0.1
        self.beta = 1.2

    def getLatencyOfLink(self, link, util):
        if not self._validateUtilization(util):
            raise ValueError("Invalid link utilization")
        bandwidth = link.bandwidth
        linkLength = link.linkLength
        pl = self.getPropogationLatency(linkLength)
        if bandwidth > 0:
            # distinguish different bandwidth model
            if util < 1:
                return min(self.alpha/(1-util), self.beta) + pl # unit: ms
            else:
                return self.beta + pl

    def getPropogationLatency(self, linkLength):
        return linkLength / SPEED_OF_LIGHT

    def _validateUtilization(self, util):
        if util >=0 and util <= 1:
            return True
        else:
            return False

    def getResourceConsumeRatioOfVNF(self, vnfType):
        # VNF_TYPE_CLASSIFIER = 0
        # VNF_TYPE_FORWARD = 1
        # VNF_TYPE_FW = 2
        # VNF_TYPE_IDS = 3
        # VNF_TYPE_MONITOR = 4
        # VNF_TYPE_LB = 5
        # VNF_TYPE_TRAFFICSHAPER = 6
        # VNF_TYPE_NAT = 7
        # VNF_TYPE_VPN = 8
        # VNF_TYPE_WOC = 9    # WAN Optimization Controller
        # VNF_TYPE_APPFW = 10 # http firewall
        # VNF_TYPE_VOC = 11

        vnfResConsRatioList = {
            # vnfType: [coresPer1GTraffic, memoryPer1GTraffic]
            # data from [2020][SIGCOMM]Contention-Aware Performance 
            # Prediction For Virtualized Network Functions
            0: [1/40.0, 1],
            1: [1/40.0, 1],
            2: [1/5.846, 1],
            3: [1/0.302, 1],
            4: [1/0.612, 1],
            5: [1/5.040, 1],
            6: [1/0.612, 1],    # need measurement
            7: [1/0.300, 1],
            8: [1/0.400, 1],
            9: [1/1.1, 1],      # [2018][TON]Middlebox-Based Packet-Level
                                # Redundancy Elimination Over 
                                # Encrypted Network Traffic
            10: [0.1, 1],   # pfSense
            11: [1/1.1, 1]    # [2018][TON]Middlebox-Based Packet-Level
                                # Redundancy Elimination Over 
                                # Encrypted Network Traffic
        }

        return vnfResConsRatioList[vnfType]

    def getExpectedServerResource(self, vnfType, trafficDemand):
        resConRatio = self.getResourceConsumeRatioOfVNF(vnfType)
        for index in range(len(resConRatio)):
            resConRatio[index] = math.ceil(
                resConRatio[index] * trafficDemand)

        resConRatio.append(trafficDemand)

        return resConRatio

    def getMaxLatencyOfVNF(self, vnfType):
        # VNF_TYPE_CLASSIFIER = 0
        # VNF_TYPE_FORWARD = 1
        # VNF_TYPE_FW = 2
        # VNF_TYPE_IDS = 3
        # VNF_TYPE_MONITOR = 4
        # VNF_TYPE_LB = 5
        # VNF_TYPE_TRAFFICSHAPER = 6
        # VNF_TYPE_NAT = 7
        # VNF_TYPE_VPN = 8
        # VNF_TYPE_WOC = 9    # WAN Optimization Controller
        # VNF_TYPE_APPFW = 10 # http firewall
        # VNF_TYPE_VOC = 11

        vnfMaxLatencyDict = {
            # vnfType: maxLatencyOfVNF
            # \rho = \delta_{f} / ceil(\delta_{f} * D^c_{sd}) * Latency_{max}
            # where ceil(\delta_{f} * D^c_{sd}) = ResourceAllocation^{sd,c}_{u}
            0: 5,
            1: 5,
            2: 5,
            3: 5,
            4: 5,
            5: 5,
            6: 5,
            7: 5,
            8: 5,
            9: 5,
            10: 5,
            11: 5
        }

        return vnfMaxLatencyDict[vnfType]

    def getLatencyOfVNF(self, vnfType, trafficDemand):
        # only consider cpu core resource
        maxLatency = self.getMaxLatencyOfVNF(vnfType)
        resConRatio = self.getResourceConsumeRatioOfVNF(vnfType)[0]
        consumedRes = trafficDemand * resConRatio
        reservedRes = math.ceil(trafficDemand * resConRatio)
        latency = consumedRes / reservedRes * maxLatency
        return latency
