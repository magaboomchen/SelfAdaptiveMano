#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid
import logging
from sam.base.rateLimiter import RateLimiterConfig

from sam.base.slo import SLO
from sam.base.routingMorphic import RoutingMorphic
from sam.base.messageAgent import SIMULATOR_ZONE
from sam.base.sfc import SFC, SFCI, APP_TYPE_NORTHSOUTH_WEBSITE
from sam.base.path import MAPPING_TYPE_MMLPSFC, ForwardingPathSet
from sam.base.test.fixtures.srv6MorphicDict import srv6MorphicDictTemplate
from sam.base.vnf import PREFERRED_DEVICE_TYPE_SERVER, VNF, VNFI,  \
                            VNF_TYPE_RATELIMITER, VNF_TYPE_FORWARD
from sam.base.server import Server, SERVER_TYPE_CLASSIFIER, SERVER_TYPE_NFVI
from sam.base.switch import SWITCH_TYPE_DCNGATEWAY, SWITCH_TYPE_NPOP, Switch
from sam.test.testBase import DCN_GATEWAY_IP, TestBase, WEBSITE_REAL_IP, CLASSIFIER_DATAPATH_IP

MANUAL_TEST = True

CLASSIFIER_DATAPATH_IP = "2.2.0.2"
CLASSIFIER_DATAPATH_MAC = "00:1b:21:c0:8f:ae"   # ignore this
CLASSIFIER_CONTROL_IP = "192.168.0.194" # ignore this
CLASSIFIER_SERVERID = 10001

SFF1_DATAPATH_IP = "2.2.96.3"
SFF1_DATAPATH_MAC = "b8:ca:3a:65:f7:fa" # ignore this
SFF1_CONTROLNIC_IP = "192.168.8.17" # ignore this
SFF1_CONTROLNIC_MAC = "b8:ca:3a:65:f7:f8"   # ignore this
SFF1_SERVERID = 11281

SWITCH_SFF1_SWITCHID = 768
SWITCH_SFF1_LANIP = "2.2.96.0"


class TestSimulatorBase(TestBase):
    MAXSFCIID = 0
    sfciCounter = 0
    logging.getLogger("pika").setLevel(logging.WARNING)

    def genClassifier(self, datapathIfIP=None, serverBasedClassifier=True):
        if serverBasedClassifier:
            classifier = Server("ens3", datapathIfIP, SERVER_TYPE_CLASSIFIER)
            classifier.setServerID(CLASSIFIER_SERVERID)
            classifier._serverDatapathNICIP = CLASSIFIER_DATAPATH_IP
            classifier._ifSet["ens3"] = {}
            classifier._ifSet["ens3"]["IP"] = CLASSIFIER_CONTROL_IP
            classifier._serverDatapathNICMAC = CLASSIFIER_DATAPATH_MAC
        else:
            classifier = Switch(0, SWITCH_TYPE_DCNGATEWAY, DCN_GATEWAY_IP,
                                                    programmable=True)
        return classifier

    def genUniDirectionSFC(self, classifier, sfcLength=1):
        sfcUUID = uuid.uuid1()
        vNFTypeSequence = [VNF_TYPE_RATELIMITER] * sfcLength
        vnfSequence = [VNF(uuid.uuid1(), VNF_TYPE_RATELIMITER,
                            RateLimiterConfig(maxMbps=100),
                            PREFERRED_DEVICE_TYPE_SERVER)] * sfcLength
        maxScalingInstanceNumber = 1
        backupInstanceNumber = 0
        applicationType = APP_TYPE_NORTHSOUTH_WEBSITE
        routingMorphic = RoutingMorphic()
        routingMorphic.from_dict(srv6MorphicDictTemplate)
        direction1 = {
            'ID': 0,
            'source': {'node': None, 'IPv4':"*"},
            'ingress': classifier,
            'match': {'srcIP': "*",'dstIP':WEBSITE_REAL_IP,
                'srcPort': "*",'dstPort': "*",'proto': "*"},
            'egress': classifier,
            'destination': {'node': None, 'IPv4':WEBSITE_REAL_IP}
        }
        directions = [direction1]
        slo = SLO(latencyBound=35, throughput=0.1)
        return SFC(sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
            backupInstanceNumber, applicationType, directions,
            {'zone': SIMULATOR_ZONE}, slo=slo, routingMorphic=routingMorphic,
            vnfSequence=vnfSequence)

    def genUniDirection10BackupServerNFVISFCI(self, mappedVNFISeq=True,
                                            sfcLength=1,
                                            serverBasedClassifier=True,
                                            vnfType=VNF_TYPE_FORWARD):
        if mappedVNFISeq:
            vnfiSequence = self.gen10BackupServerVNFISequence(sfcLength,
                                            vnfType=VNF_TYPE_FORWARD)
        else:
            vnfiSequence = None
        return SFCI(self.assignSFCIID(), vnfiSequence, None,
            self.genUniDirection10BackupServerBasedForwardingPathSet(sfcLength, 
                                                        serverBasedClassifier))

    def gen10BackupServerVNFISequence(self, sfcLength=1, vnfType=VNF_TYPE_FORWARD):
        # hard-code function
        vnfiSequence = []
        for index in range(sfcLength):
            vnfiSequence.append([])
            for iN in range(1):
                server = Server("ens3", SFF1_DATAPATH_IP, SERVER_TYPE_NFVI)
                server.setServerID(SFF1_SERVERID)
                server.setControlNICIP(SFF1_CONTROLNIC_IP)
                server.setControlNICMAC(SFF1_CONTROLNIC_MAC)
                server.setDataPathNICMAC(SFF1_DATAPATH_MAC)
                vnfi = VNFI(vnfType, vnfType=vnfType,
                    vnfiID=uuid.uuid1(), node=server)
                vnfiSequence[index].append(vnfi)
        return vnfiSequence

    def genUniDirection10BackupServerBasedForwardingPathSet(self, sfciLength=1, 
                                                    serverBasedClassifier=False):
        # please ref /sam/base/path.py
        # This function generate a sfc forwarding path for sfc "ingress->L2Forwarding->egress"
        # The primary forwarding path has two stage, the first stage is "ingress->L2Forwarding",
        # the second stage is "L2Forwarding->egress".
        # Each stage is a list of layeredNodeIDTuple which format is (stageIndex, nodeID)
        if sfciLength == 1:
            if serverBasedClassifier:
                d1FP = [
                        [(0,CLASSIFIER_SERVERID),(0,0),(0,256),(0,768),(0,SFF1_SERVERID)], # (stageIndex, nodeID)
                        [(1,SFF1_SERVERID),(1,768),(1,256),(1,0),(1,CLASSIFIER_SERVERID)]
                    ]
            else:
                d1FP = [
                        [(0,0),(0,256),(0,768),(0,SFF1_SERVERID)], # (stageIndex, nodeID)
                        [(1,SFF1_SERVERID),(1,768),(1,256),(1,0)]
                    ]
        elif sfciLength == 2:
            if serverBasedClassifier:
                d1FP = [
                        [(0,CLASSIFIER_SERVERID),(0, 0), (0, 256), (0, 768), (0, SFF1_SERVERID)],
                        [(1, SFF1_SERVERID), (1, SFF1_SERVERID)],
                        [(2, SFF1_SERVERID), (2, 768), (2, 256), (2, 0),(2,CLASSIFIER_SERVERID)]
                    ]
            else:
                d1FP = [
                        [(0, 0), (0, 256), (0, 768), (0, SFF1_SERVERID)],
                        [(1, SFF1_SERVERID), (1, SFF1_SERVERID)],
                        [(2, SFF1_SERVERID), (2, 768), (2, 256), (2, 0)]
                    ]
        elif sfciLength == 3:
            if serverBasedClassifier:
                d1FP = [
                        [(0,CLASSIFIER_SERVERID),(0, 0), (0, 256), (0, 768), (0, SFF1_SERVERID)],
                        [(1, SFF1_SERVERID), (1, SFF1_SERVERID)],
                        [(2, SFF1_SERVERID), (2, SFF1_SERVERID)],
                        [(3, SFF1_SERVERID), (3, 768), (3, 256), (3, 0),(3,CLASSIFIER_SERVERID)]
                    ]
            else:
                d1FP = [
                        [(0, 0), (0, 256), (0, 768), (0, SFF1_SERVERID)],
                        [(1, SFF1_SERVERID), (1, SFF1_SERVERID)],
                        [(2, SFF1_SERVERID), (2, SFF1_SERVERID)],
                        [(3, SFF1_SERVERID), (3, 768), (3, 256), (3, 0)]
                    ]
        else:
            raise ValueError("Unimplement sfci length!")
        primaryForwardingPath = {1:d1FP}   
        mappingType = MAPPING_TYPE_MMLPSFC # This is your mapping algorithm type
        backupForwardingPath = {}   # you don't need to care about backupForwardingPath
        return ForwardingPathSet(primaryForwardingPath, mappingType,
                                    backupForwardingPath)

    def genUniDirection10BackupP4NFVISFCI(self, mappedVNFISeq=True, sfcLength=1, serverBasedClassifier=True):
        if mappedVNFISeq:
            vnfiSequence = self.gen10BackupP4VNFISequence(sfcLength)
        else:
            vnfiSequence = None
        return SFCI(self.assignSFCIID(), vnfiSequence, None,
            self.genUniDirection10BackupP4BasedForwardingPathSet(sfcLength, serverBasedClassifier))

    def gen10BackupP4VNFISequence(self, sfcLength=1):
        # hard-code function
        vnfiSequence = []
        for index in range(sfcLength):
            vnfiSequence.append([])
            for iN in range(1):
                switch = Switch(SWITCH_SFF1_SWITCHID, SWITCH_TYPE_NPOP, 
                                    SWITCH_SFF1_LANIP, programmable=True)
                vnfi = VNFI(VNF_TYPE_FORWARD, vnfType=VNF_TYPE_FORWARD,
                    vnfiID=uuid.uuid1(), node=switch)
                vnfiSequence[index].append(vnfi)
        return vnfiSequence

    def genUniDirection10BackupP4BasedForwardingPathSet(self, sfciLength=1,
                                                serverBasedClassifier=False):
        # please ref /sam/base/path.py
        # This function generate a sfc forwarding path for sfc "ingress->L2Forwarding->egress"
        # The primary forwarding path has two stage, the first stage is "ingress->L2Forwarding",
        # the second stage is "L2Forwarding->egress".
        # Each stage is a list of layeredNodeIDTuple which format is (stageIndex, nodeID)
        if sfciLength == 1:
            if serverBasedClassifier:
                d1FP = [
                        [(0,CLASSIFIER_SERVERID),(0,0),(0,256),(0,SWITCH_SFF1_SWITCHID)], # (stageIndex, nodeID)
                        [(1,SWITCH_SFF1_SWITCHID),(1,256),(1,0),(1,CLASSIFIER_SERVERID)]
                    ]
            else:
                d1FP = [
                        [(0,0),(0,256),(0,SWITCH_SFF1_SWITCHID)], # (stageIndex, nodeID)
                        [(1,SWITCH_SFF1_SWITCHID),(1,256),(1,0)]
                    ]
        elif sfciLength == 2:
            if serverBasedClassifier:
                d1FP = [
                        [(0,CLASSIFIER_SERVERID),(0, 0), (0, 256), (0, SWITCH_SFF1_SWITCHID)],
                        [(1, SWITCH_SFF1_SWITCHID), (1, SWITCH_SFF1_SWITCHID)],
                        [(2, SWITCH_SFF1_SWITCHID), (2, 256), (2, 0),(2,CLASSIFIER_SERVERID)]
                    ]
            else:
                d1FP = [
                        [(0, 0), (0, 256), (0, SWITCH_SFF1_SWITCHID)],
                        [(1, SWITCH_SFF1_SWITCHID), (1, SWITCH_SFF1_SWITCHID)],
                        [(2, SWITCH_SFF1_SWITCHID), (2, 256), (2, 0)]
                    ]
        elif sfciLength == 3:
            if serverBasedClassifier:
                d1FP = [
                        [(0,CLASSIFIER_SERVERID),(0, 0), (0, 256), (0, SWITCH_SFF1_SWITCHID)],
                        [(1, SWITCH_SFF1_SWITCHID), (1, SWITCH_SFF1_SWITCHID)],
                        [(2, SWITCH_SFF1_SWITCHID), (2, SWITCH_SFF1_SWITCHID)],
                        [(3, SWITCH_SFF1_SWITCHID), (3, 256), (3, 0),(3,CLASSIFIER_SERVERID)]
                    ]
            else:
                d1FP = [
                        [(0, 0), (0, 256), (0, SWITCH_SFF1_SWITCHID)],
                        [(1, SWITCH_SFF1_SWITCHID), (1, SWITCH_SFF1_SWITCHID)],
                        [(2, SWITCH_SFF1_SWITCHID), (2, SWITCH_SFF1_SWITCHID)],
                        [(3, SWITCH_SFF1_SWITCHID), (3, 256), (3, 0)]
                    ]
        else:
            raise ValueError("Unimplement sfci length!")
        primaryForwardingPath = {1:d1FP}   
        mappingType = MAPPING_TYPE_MMLPSFC # This is your mapping algorithm type
        backupForwardingPath = {}   # you don't need to care about backupForwardingPath
        return ForwardingPathSet(primaryForwardingPath, mappingType,
                                    backupForwardingPath)
