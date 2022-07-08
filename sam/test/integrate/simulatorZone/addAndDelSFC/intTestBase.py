#!/usr/bin/python
# -*- coding: UTF-8 -*-

import time
import logging
import uuid

from sam.base.compatibility import screenInput
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.messageAgent import SIMULATOR_ZONE
from sam.base.rateLimiter import RateLimiterConfig
from sam.base.acl import ACL_ACTION_ALLOW, ACL_PROTO_UDP, ACLTuple
from sam.base.routingMorphic import IPV4_ROUTE_PROTOCOL, IPV6_ROUTE_PROTOCOL, \
                                        ROCEV1_ROUTE_PROTOCOL, SRV6_ROUTE_PROTOCOL
from sam.base.sfc import APP_TYPE_BEST_EFFORT, APP_TYPE_HIGH_AVA, \
                        APP_TYPE_LARGE_BANDWIDTH, APP_TYPE_LARGE_CONNECTION, \
                        APP_TYPE_LOW_LATENCY, SFC, SFCI
from sam.base.shellProcessor import ShellProcessor
from sam.base.slo import SLO
from sam.base.vnf import PREFERRED_DEVICE_TYPE_P4, PREFERRED_DEVICE_TYPE_SERVER, \
                            VNF, VNF_TYPE_FW, VNF_TYPE_MONITOR, VNF_TYPE_RATELIMITER
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer
from sam.test.testBase import APP1_REAL_IP, APP2_REAL_IP, APP3_REAL_IP, \
                                APP4_REAL_IP, APP5_REAL_IP, TestBase


class IntTestBaseClass(TestBase):
    MAXSFCIID = 0
    sfciCounter = 0
    logging.getLogger("pika").setLevel(logging.WARNING)

    def common_setup(self):
        logConfigur = LoggerConfigurator(__name__, './log',
                                            'testBaseClass.log',
                                            level='debug')
        self.logger = logConfigur.getLogger()
        self.logger.setLevel(logging.DEBUG)

        # setup
        self.sP = ShellProcessor()
        self.cleanLog()
        self.clearQueue()
        self.killAllModule()
        self.cleanSFCAndSFCIInDB()
        time.sleep(3)
        logging.info("Please start dispatcher, mediator and simulator!"\
                        " Then press Any key to continue!")
        screenInput()

    def common_teardown(self):
        self.clearQueue()
        self.killAllModule()
        # self.cleanSFCAndSFCIInDB()

    def getSFCFromDB(self, sfcUUID):
        self._oib = OrchInfoBaseMaintainer("localhost", "dbAgent", "123",
                                            False)
        self.sfcInDB = self._oib.getSFC4DB(sfcUUID)
        return self.sfcInDB

    def cleanSFCAndSFCIInDB(self):
        self._oib = OrchInfoBaseMaintainer("localhost", "dbAgent", "123",
                                            True)

    def genLargeBandwidthSFC(self, classifier):
        sfcUUID = uuid.uuid1()
        vNFTypeSequence = [VNF_TYPE_MONITOR, VNF_TYPE_RATELIMITER]
        vnfSequence = [VNF(uuid.uuid1(), VNF_TYPE_MONITOR,
                            None, PREFERRED_DEVICE_TYPE_P4),
                        VNF(uuid.uuid1(), VNF_TYPE_RATELIMITER,
                            RateLimiterConfig(maxMbps=100),
                            PREFERRED_DEVICE_TYPE_P4)]
        maxScalingInstanceNumber = 1
        backupInstanceNumber = 0
        applicationType = APP_TYPE_LARGE_BANDWIDTH
        routingMorphic = SRV6_ROUTE_PROTOCOL
        direction1 = {
            'ID': 0,
            'source': {'node': None, 'IPv4':"*"},
            'ingress': classifier,
            'match': {'srcIP': "*",'dstIP':APP1_REAL_IP,
                'srcPort': "*",'dstPort': "*",'proto': "*"},
            'egress': classifier,
            'destination': {'node': None, 'IPv4':APP1_REAL_IP}
        }
        directions = [direction1]
        slo = SLO(throughput=10, latencyBound=100, availability=0.999, \
                    connections=10)
        return SFC(sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
            backupInstanceNumber, applicationType, directions,
            {'zone': SIMULATOR_ZONE}, slo=slo, routingMorphic=routingMorphic,
            vnfSequence=vnfSequence)

    def genHighAvaSFC(self, classifier):
        sfcUUID = uuid.uuid1()
        vNFTypeSequence = [VNF_TYPE_FW]
        vnfSequence = [VNF(uuid.uuid1(), VNF_TYPE_FW,
                            self.genFWConfigExample(IPV4_ROUTE_PROTOCOL),
                            PREFERRED_DEVICE_TYPE_SERVER)]
        maxScalingInstanceNumber = 1
        backupInstanceNumber = 0
        applicationType = APP_TYPE_HIGH_AVA
        routingMorphic = IPV4_ROUTE_PROTOCOL
        direction1 = {
            'ID': 0,
            'source': {'node': None, 'IPv4':"*"},
            'ingress': classifier,
            'match': {'srcIP': "*",'dstIP':APP2_REAL_IP,
                'srcPort': "*",'dstPort': "*",'proto': "*"},
            'egress': classifier,
            'destination': {'node': None, 'IPv4':APP2_REAL_IP}
        }
        directions = [direction1]
        slo = SLO(throughput=1, latencyBound=100, availability=0.9995, \
                    connections=10)
        return SFC(sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
            backupInstanceNumber, applicationType, directions,
            {'zone': SIMULATOR_ZONE}, slo=slo, routingMorphic=routingMorphic,
            vnfSequence=vnfSequence)

    def genLowLatencySFC(self, classifier):
        sfcUUID = uuid.uuid1()
        vNFTypeSequence = [VNF_TYPE_MONITOR]
        vnfSequence = [VNF(uuid.uuid1(), VNF_TYPE_MONITOR,
                            None, PREFERRED_DEVICE_TYPE_P4)]
        maxScalingInstanceNumber = 1
        backupInstanceNumber = 0
        applicationType = APP_TYPE_LOW_LATENCY
        routingMorphic = ROCEV1_ROUTE_PROTOCOL
        direction1 = {
            'ID': 0,
            'source': {'node': None, 'IPv4':"*"},
            'ingress': classifier,
            'match': {'srcIP': "*",'dstIP':APP3_REAL_IP,
                'srcPort': "*",'dstPort': "*",'proto': "*"},
            'egress': classifier,
            'destination': {'node': None, 'IPv4':APP3_REAL_IP}
        }
        directions = [direction1]
        slo = SLO(throughput=1, latencyBound=10, availability=0.999, \
                    connections=10)
        return SFC(sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
            backupInstanceNumber, applicationType, directions,
            {'zone': SIMULATOR_ZONE}, slo=slo, routingMorphic=routingMorphic,
            vnfSequence=vnfSequence)

    def genLargeConnectionSFC(self, classifier):
        sfcUUID = uuid.uuid1()
        vNFTypeSequence = [VNF_TYPE_MONITOR, VNF_TYPE_FW]
        vnfSequence = [VNF(uuid.uuid1(), VNF_TYPE_MONITOR,
                            None, PREFERRED_DEVICE_TYPE_P4),
                        VNF(uuid.uuid1(), VNF_TYPE_FW,
                            self.genFWConfigExample(IPV6_ROUTE_PROTOCOL),
                            PREFERRED_DEVICE_TYPE_P4)]
        maxScalingInstanceNumber = 1
        backupInstanceNumber = 0
        applicationType = APP_TYPE_LARGE_CONNECTION
        routingMorphic = IPV6_ROUTE_PROTOCOL
        direction1 = {
            'ID': 0,
            'source': {'node': None, 'IPv4':"*"},
            'ingress': classifier,
            'match': {'srcIP': "*",'dstIP':APP4_REAL_IP,
                'srcPort': "*",'dstPort': "*",'proto': "*"},
            'egress': classifier,
            'destination': {'node': None, 'IPv4':APP4_REAL_IP}
        }
        directions = [direction1]
        slo = SLO(throughput=1, latencyBound=100, availability=0.999, \
                    connections=10000)
        return SFC(sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
            backupInstanceNumber, applicationType, directions,
            {'zone': SIMULATOR_ZONE}, slo=slo, routingMorphic=routingMorphic,
            vnfSequence=vnfSequence)

    def genBestEffortSFC(self, classifier):
        sfcUUID = uuid.uuid1()
        vNFTypeSequence = [VNF_TYPE_RATELIMITER]
        vnfSequence = [VNF(uuid.uuid1(), VNF_TYPE_RATELIMITER,
                            RateLimiterConfig(maxMbps=100),
                            PREFERRED_DEVICE_TYPE_SERVER)]
        maxScalingInstanceNumber = 1
        backupInstanceNumber = 0
        applicationType = APP_TYPE_BEST_EFFORT
        routingMorphic = IPV4_ROUTE_PROTOCOL
        direction1 = {
            'ID': 0,
            'source': {'node': None, 'IPv4':"*"},
            'ingress': classifier,
            'match': {'srcIP': "*",'dstIP':APP5_REAL_IP,
                'srcPort': "*",'dstPort': "*",'proto': "*"},
            'egress': classifier,
            'destination': {'node': None, 'IPv4':APP5_REAL_IP}
        }
        directions = [direction1]
        slo = SLO(throughput=0.1, latencyBound=200, availability=0.99, \
                    connections=10)
        return SFC(sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
            backupInstanceNumber, applicationType, directions,
            {'zone': SIMULATOR_ZONE}, slo=slo, routingMorphic=routingMorphic,
            vnfSequence=vnfSequence)

    def genFWConfigExample(self, routingMorphic):
        fwConfigList = []
        if routingMorphic == IPV4_ROUTE_PROTOCOL:
            dstAddr="3.3.3.3"
        elif routingMorphic == IPV6_ROUTE_PROTOCOL:
            dstAddr="2026:0000::"
        else:
            dstAddr="3.3.3.3"
        entry = ACLTuple(ACL_ACTION_ALLOW, ACL_PROTO_UDP, dstAddr=dstAddr)
        fwConfigList.append(entry)
        return fwConfigList

    def genSFCITemplate(self):
        vnfiSequence = None
        return SFCI(self.assignSFCIID(), vnfiSequence, None, None)
