#!/usr/bin/python
# -*- coding: UTF-8 -*-

import math

SPEED_OF_LIGHT = 3.0 * pow(10, 8)
P4_LATENCY = 0.001 * 0.001


class PerformanceModel(object):
    def __init__(self):
        pass
        # There may be a bug in LoggerConfigurator
        # It will consume a lot of memory!
        # logConfigur = LoggerConfigurator(__name__, './log',
        #     'performanceModel.log', level='debug')
        # self.logger = logConfigur.getLogger()

    def loadInterferenceModel(self, filepathToModel):
        pass

    def getThroughput(self, serverArchitecture, targetNFType, competitorsList):
        pass

    def getLatencyOfLink(self, link, util):
        if not self._validateUtilization(util):
            pass
            # self.logger.error(
            #     "Invalid link utilization {0} for link {1}".format(
            #         util, link))
            # raise ValueError(
            #     "Invalid link utilization {0} for link {1}".format(
            #         util, link))
        bandwidth = link.bandwidth
        linkLength = link.linkLength
        pl = self.getPropogationLatency(linkLength)
        # distinguish different bandwidth model
        if bandwidth == 0.155:
            self.alpha = 0.65
            self.beta = 7.74
        elif bandwidth == 1:
            # real measurement of PICA8 ToR
            self.alpha = 0.1
            self.beta = 1.2
            # https://people.ucsc.edu/~warner/Bufs/Arista7800R3SwitchArchitectureWP.pdf
            # self.alpha = 1
            # self.beta = 40
        elif bandwidth == 2.5:
            self.alpha = 0.04
            self.beta = 0.48
        elif bandwidth == 10:
            self.alpha = 0.01
            self.beta = 0.12
        elif bandwidth == 20:
            self.alpha = 0.005
            self.beta = 0.06
        elif bandwidth == 100:
            self.alpha = 0.001
            self.beta = 400
        elif bandwidth == 400:
            self.alpha = 0.001/4
            self.beta = 100
        else:
            self.alpha = 0.1 / bandwidth
            self.beta = 1.2 / bandwidth
            # raise ValueError(
            #     "Link latency model: unsupport bandwidth {0}".format(
            #         bandwidth))

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
        # VNF_TYPE_RATELIMITER = 6
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
            6: [1/10.0, 1],    # need measurement
            7: [1/0.300, 1],
            8: [1/0.400, 1],
            9: [1/1.1, 1],      # [2018][TON]Middlebox-Based Packet-Level
                                # Redundancy Elimination Over 
                                # Encrypted Network Traffic
            10: [0.1, 1],   # pfSense
            11: [1/1.1, 1],    # [2018][TON]Middlebox-Based Packet-Level
                                # Redundancy Elimination Over 
                                # Encrypted Network Traffic
            12: [1/1.1, 1],     # need measurement
            13: [1/5.846, 1],
            14: [1/0.300, 1],
            15: [1/1.1, 1],     # need measurement
        }

        return vnfResConsRatioList[vnfType]

    def getExpectedServerResource(self, vnfType, trafficDemand):
        # type: (str, float) -> None
        # traffidcDemand's unit is Gbps
        resConRatio = self.getResourceConsumeRatioOfVNF(vnfType)
        for index in range(len(resConRatio)):
            resConRatio[index] = math.ceil(
                resConRatio[index] * trafficDemand)

        resConRatio.append(trafficDemand)

        return resConRatio

    def getVNFIExpectedThroughput(self, vnfType, cpuCoresNum):
        resConRatio = self.getResourceConsumeRatioOfVNF(vnfType)
        return cpuCoresNum * 1.0 / resConRatio[0] * 1.0

    def getMaxLatencyOfVNF(self, vnfType):
        # VNF_TYPE_CLASSIFIER = 0
        # VNF_TYPE_FORWARD = 1
        # VNF_TYPE_FW = 2
        # VNF_TYPE_IDS = 3
        # VNF_TYPE_MONITOR = 4
        # VNF_TYPE_LB = 5
        # VNF_TYPE_RATELIMITER = 6
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
            11: 5,
            12: 5,
            13: 5,
            14: 5,
            15: 5,
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

    def getSwitchLatency(self):
        return P4_LATENCY
