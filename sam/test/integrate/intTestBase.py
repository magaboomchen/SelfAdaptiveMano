#!/usr/bin/python
# -*- coding: UTF-8 -*-

import time
import uuid

from sam.base.compatibility import screenInput
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.messageAgent import SIMULATOR_ZONE
from sam.base.rateLimiter import RateLimiterConfig
from sam.base.routingMorphic import RoutingMorphic, IPV4_ROUTE_PROTOCOL, \
            IPV6_ROUTE_PROTOCOL
from sam.base.test.fixtures.ipv4MorphicDict import ipv4MorphicDictTemplate
from sam.base.test.fixtures.ipv6MorphicDict import ipv6MorphicDictTemplate
from sam.base.test.fixtures.srv6MorphicDict import srv6MorphicDictTemplate
from sam.base.test.fixtures.roceV1MorphicDict import roceV1MorphicDictTemplate
from sam.base.sfc import SFC, SFCI
from sam.base.sfcConstant import APP_TYPE_BEST_EFFORT, APP_TYPE_HIGH_AVA, \
                        APP_TYPE_LARGE_BANDWIDTH, APP_TYPE_LARGE_CONNECTION, \
                        APP_TYPE_LOW_LATENCY, AUTO_SCALE, SFC_DIRECTION_0, \
                        SFC_DIRECTION_1
from sam.base.shellProcessor import ShellProcessor
from sam.base.slo import SLO
from sam.base.vnf import PREFERRED_DEVICE_TYPE_P4, VNF, VNF_TYPE_FW, \
        PREFERRED_DEVICE_TYPE_SERVER, VNF_TYPE_MONITOR, VNF_TYPE_RATELIMITER, \
        VNFI_RESOURCE_QUOTA_SMALL
from sam.measurement.dcnInfoBaseMaintainer import DCNInfoBaseMaintainer
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer
from sam.test.testBase import APP1_REAL_IP, APP1_REAL_IPV6, APP2_REAL_IP, APP3_REAL_GID, APP3_REAL_IP, APP4_REAL_IP, \
                                APP4_REAL_IPV6, APP5_REAL_IP, APP6_REAL_IP, TestBase


class IntTestBaseClass(TestBase):
    MAXSFCIID = 0
    sfciCounter = 0

    def common_setup(self):
        logConfigur = LoggerConfigurator(__name__, './log',
                                            'testBaseClass.log',
                                            level='debug')
        self.logger = logConfigur.getLogger()

        # setup
        self.sP = ShellProcessor()
        self.cleanLog()
        self.clearQueue()
        self.killAllModule()
        self.dropRequestAndSFCAndSFCITableInDB()
        self.initZone()
        time.sleep(3)
        self._dib = DCNInfoBaseMaintainer()
        self._oib = OrchInfoBaseMaintainer("localhost", "dbAgent", "123",
                                            False)
        self.logger.info("Please start dispatcher, mediator and simulator!"\
                        " Then press Any key to continue!")
        screenInput()

    def common_teardown(self):
        self.clearQueue()
        self.killAllModule()

    def getSFCFromDB(self, sfcUUID):
        self.sfcInDB = self._oib.getSFC4DB(sfcUUID)
        return self.sfcInDB

    def getSFCIIDListFromDB(self, sfcUUID):
        sfciIDList = self._oib.getSFCCorrespondingSFCIID4DB(sfcUUID)
        return sfciIDList

    def getSFCIFromDB(self, sfciID):
        return self._oib.getSFCI4DB(sfciID)

    def genLargeBandwidthSFC(self, classifier, zone=SIMULATOR_ZONE,
                                scalingMode=AUTO_SCALE):
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
        routingMorphic = RoutingMorphic()
        routingMorphic.from_dict(srv6MorphicDictTemplate)
        direction0 = {
            'ID': SFC_DIRECTION_0,
            'source': {'node': None, 'IPv4':"*", 'IPv6':"*"},
            'ingress': classifier,
            'match': {'srcIP': "*",'dstIP':APP1_REAL_IPV6,
                'srcPort': "*",'dstPort': "*",'proto': "*"},
            'egress': classifier,
            'destination': {'node': None, 'IPv4':APP1_REAL_IP,
                                          'IPv6':APP1_REAL_IPV6}
        }
        direction1 ={
            'ID': SFC_DIRECTION_1,
            'source': {'node': None, 'IPv4':APP1_REAL_IP, 
                                     'IPv6':APP1_REAL_IPV6},
            'ingress': classifier,
            'match': {'srcIP': APP1_REAL_IPV6,'dstIP':"*",
                'srcPort': "*",'dstPort': "*",'proto': "*"},
            'egress': classifier,
            'destination': {'node': None, 'IPv4':"*",
                                          'IPv6':"*"}
        }
        directions = [direction0, direction1]
        # directions = [direction0]
        slo = SLO(throughput=5, latency=100, availability=0.999, \
                    connections=10)
        return SFC(sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
                    backupInstanceNumber, applicationType, directions,
                    {'zone': zone}, slo=slo, routingMorphic=routingMorphic,
                    vnfSequence=vnfSequence, scalingMode=scalingMode,
                    vnfiResourceQuota=VNFI_RESOURCE_QUOTA_SMALL)

    def genHighAvaSFC(self, classifier, zone=SIMULATOR_ZONE,
                        scalingMode=AUTO_SCALE):
        sfcUUID = uuid.uuid1()
        vNFTypeSequence = [VNF_TYPE_FW]
        vnfSequence = [VNF(uuid.uuid1(), VNF_TYPE_FW,
                            self.genFWConfigExample(IPV4_ROUTE_PROTOCOL),
                            PREFERRED_DEVICE_TYPE_SERVER)]
        maxScalingInstanceNumber = 1
        backupInstanceNumber = 0
        applicationType = APP_TYPE_HIGH_AVA
        routingMorphic = RoutingMorphic()
        routingMorphic.from_dict(ipv4MorphicDictTemplate)
        direction0 = {
            'ID': SFC_DIRECTION_0,
            'source': {'node': None, 'IPv4':"*"},
            'ingress': classifier,
            'match': {'srcIP': "*",'dstIP':APP2_REAL_IP,
                'srcPort': "*",'dstPort': "*",'proto': "*"},
            'egress': classifier,
            'destination': {'node': None, 'IPv4':APP2_REAL_IP}
        }
        directions = [direction0]
        slo = SLO(throughput=1, latency=100, availability=0.9995, \
                    connections=10)
        return SFC(sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
                    backupInstanceNumber, applicationType, 
                    directions = directions,
                    attributes={'zone': zone}, slo=slo,
                    routingMorphic=routingMorphic,
                    vnfSequence=vnfSequence, 
                    scalingMode=scalingMode,
                    vnfiResourceQuota=VNFI_RESOURCE_QUOTA_SMALL)

    def genLowLatencySFC(self, classifier, zone=SIMULATOR_ZONE,
                            scalingMode=AUTO_SCALE):
        sfcUUID = uuid.uuid1()
        vNFTypeSequence = [VNF_TYPE_MONITOR]
        vnfSequence = [VNF(uuid.uuid1(), VNF_TYPE_MONITOR,
                            None, PREFERRED_DEVICE_TYPE_P4)]
        maxScalingInstanceNumber = 1
        backupInstanceNumber = 0
        applicationType = APP_TYPE_LOW_LATENCY
        routingMorphic = RoutingMorphic()
        routingMorphic.from_dict(roceV1MorphicDictTemplate)
        direction0 = {
            'ID': SFC_DIRECTION_0,
            'source': {'node': None, 'IPv4':"*", 'RoceV1':"*"},
            'ingress': classifier,
            'match': {'srcIP': "*",'dstIP':APP3_REAL_GID,
                'srcPort': "*",'dstPort': "*",'proto': "*"},
            'egress': classifier,
            'destination': {'node': None, 'IPv4':APP3_REAL_IP, 'RoceV1':APP3_REAL_GID}
        }
        directions = [direction0]
        slo = SLO(throughput=1, latency=10, availability=0.999, \
                    connections=10)
        return SFC(sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
                    backupInstanceNumber, applicationType, directions,
                    {'zone': zone}, slo=slo, routingMorphic=routingMorphic,
                    vnfSequence=vnfSequence, scalingMode=scalingMode,
                    vnfiResourceQuota=VNFI_RESOURCE_QUOTA_SMALL)

    def genLargeConnectionSFC(self, classifier, zone=SIMULATOR_ZONE,
                                scalingMode=AUTO_SCALE):
        sfcUUID = uuid.uuid1()
        vNFTypeSequence = [VNF_TYPE_RATELIMITER, VNF_TYPE_FW]
        vnfSequence = [VNF(uuid.uuid1(), VNF_TYPE_RATELIMITER,
                            RateLimiterConfig(maxMbps=100), PREFERRED_DEVICE_TYPE_P4),
                        VNF(uuid.uuid1(), VNF_TYPE_FW,
                            self.genFWConfigExample(IPV6_ROUTE_PROTOCOL),
                            PREFERRED_DEVICE_TYPE_P4)]
        maxScalingInstanceNumber = 1
        backupInstanceNumber = 0
        applicationType = APP_TYPE_LARGE_CONNECTION
        routingMorphic = RoutingMorphic()
        routingMorphic.from_dict(ipv6MorphicDictTemplate)
        direction0 = {
            'ID': SFC_DIRECTION_0,
            'source': {'node': None, 'IPv4':"*", 'IPv6':"*"},
            'ingress': classifier,
            'match': {'srcIP': "*",'dstIP':APP4_REAL_IPV6,
                'srcPort': "*",'dstPort': "*",'proto': "*"},
            'egress': classifier,
            'destination': {'node': None, 'IPv4':APP4_REAL_IP,
                                          'IPv6':APP4_REAL_IPV6}
        }
        directions = [direction0]
        slo = SLO(throughput=1, latency=100, availability=0.999, \
                    connections=10000)
        return SFC(sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
                    backupInstanceNumber, applicationType, directions,
                    {'zone': zone}, slo=slo, routingMorphic=routingMorphic,
                    vnfSequence=vnfSequence, scalingMode=scalingMode,
                    vnfiResourceQuota=VNFI_RESOURCE_QUOTA_SMALL)

    def genBestEffortSFC(self, classifier, zone=SIMULATOR_ZONE,
                            scalingMode=AUTO_SCALE):
        sfcUUID = uuid.uuid1()
        vNFTypeSequence = [VNF_TYPE_RATELIMITER]
        vnfSequence = [VNF(uuid.uuid1(), VNF_TYPE_RATELIMITER,
                            RateLimiterConfig(maxMbps=100),
                            PREFERRED_DEVICE_TYPE_SERVER)]
        maxScalingInstanceNumber = 1
        backupInstanceNumber = 0
        applicationType = APP_TYPE_BEST_EFFORT
        routingMorphic = RoutingMorphic()
        routingMorphic.from_dict(ipv4MorphicDictTemplate)
        direction0 = {
            'ID': SFC_DIRECTION_0,
            'source': {'node': None, 'IPv4':"*"},
            'ingress': classifier,
            'match': {'srcIP': "*",'dstIP':APP5_REAL_IP,
                'srcPort': "*",'dstPort': "*",'proto': "*"},
            'egress': classifier,
            'destination': {'node': None, 'IPv4':APP5_REAL_IP}
        }
        directions = [direction0]
        slo = SLO(throughput=0.1, latency=200, availability=0.99, \
                    connections=10)
        return SFC(sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
                    backupInstanceNumber, applicationType, directions,
                    {'zone': zone}, slo=slo, routingMorphic=routingMorphic,
                    vnfSequence=vnfSequence, scalingMode=scalingMode,
                    vnfiResourceQuota=VNFI_RESOURCE_QUOTA_SMALL)

    def genMixEquipmentSFC(self, classifier, zone=SIMULATOR_ZONE,
                            scalingMode=AUTO_SCALE):
        sfcUUID = uuid.uuid1()
        vNFTypeSequence = [VNF_TYPE_RATELIMITER, VNF_TYPE_RATELIMITER]
        vnfSequence = [VNF(uuid.uuid1(), VNF_TYPE_RATELIMITER,
                            RateLimiterConfig(maxMbps=100),
                            PREFERRED_DEVICE_TYPE_SERVER),
                       VNF(uuid.uuid1(), VNF_TYPE_RATELIMITER,
                            RateLimiterConfig(maxMbps=100),
                            PREFERRED_DEVICE_TYPE_P4)]
        maxScalingInstanceNumber = 1
        backupInstanceNumber = 0
        applicationType = APP_TYPE_BEST_EFFORT
        routingMorphic = RoutingMorphic()
        routingMorphic.from_dict(ipv4MorphicDictTemplate)
        direction0 = {
            'ID': SFC_DIRECTION_0,
            'source': {'node': None, 'IPv4':"*"},
            'ingress': classifier,
            'match': {'srcIP': "*",'dstIP':APP6_REAL_IP,
                'srcPort': "*",'dstPort': "*",'proto': "*"},
            'egress': classifier,
            'destination': {'node': None, 'IPv4':APP6_REAL_IP}
        }
        directions = [direction0]
        slo = SLO(throughput=0.1, latency=200, availability=0.99, \
                    connections=10)
        return SFC(sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
                    backupInstanceNumber, applicationType, directions,
                    {'zone': zone}, slo=slo, routingMorphic=routingMorphic,
                    vnfSequence=vnfSequence, scalingMode=scalingMode,
                    vnfiResourceQuota=VNFI_RESOURCE_QUOTA_SMALL)

    def genSFCITemplate(self, routingMorphic=None):
        vnfiSequence = None
        return SFCI(self.assignSFCIID(), vnfiSequence, None, None,
                    routingMorphic)
