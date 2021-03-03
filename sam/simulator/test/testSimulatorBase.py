#!/usr/bin/python
# -*- coding: UTF-8 -*-

import time
import logging

import pytest

from sam import base
from sam.base.sfc import *
from sam.base.vnf import *
from sam.base.server import *
from sam.base.command import *
from sam.base.socketConverter import *
from sam.base.shellProcessor import ShellProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.test.fixtures.mediatorStub import *
from sam.test.testBase import *

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


class TestSimulatorBase(TestBase):
    MAXSFCIID = 0
    sfciCounter = 0
    logging.getLogger("pika").setLevel(logging.WARNING)

    def genClassifier(self, datapathIfIP):
        classifier = Server("ens3", datapathIfIP, SERVER_TYPE_CLASSIFIER)
        classifier.setServerID(CLASSIFIER_SERVERID)
        classifier._serverDatapathNICIP = CLASSIFIER_DATAPATH_IP
        classifier._ifSet["ens3"] = {}
        classifier._ifSet["ens3"]["IP"] = CLASSIFIER_CONTROL_IP
        classifier._serverDatapathNICMAC = CLASSIFIER_DATAPATH_MAC
        return classifier

    def genUniDirectionSFC(self, classifier):
        sfcUUID = uuid.uuid1()
        vNFTypeSequence = [VNF_TYPE_FORWARD]
        maxScalingInstanceNumber = 1
        backupInstanceNumber = 0
        applicationType = APP_TYPE_NORTHSOUTH_WEBSITE
        direction1 = {
            'ID': 0,
            'source': {"IPv4":"*"},
            'ingress': classifier,
            'match': {'srcIP': "*",'dstIP':WEBSITE_REAL_IP,
                'srcPort': "*",'dstPort': "*",'proto': "*"},
            'egress': classifier,
            'destination': {"IPv4":WEBSITE_REAL_IP}
        }
        directions = [direction1]
        slo = SLO(latencyBound=35, throughput=10)
        return SFC(sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
            backupInstanceNumber, applicationType, directions,
            {'zone': SIMULATOR_ZONE}, slo=slo)

    def genUniDirection10BackupSFCI(self):
        vnfiSequence = self.gen10BackupVNFISequence()
        return SFCI(self.assignSFCIID(), vnfiSequence, None,
            self.genUniDirection10BackupForwardingPathSet())

    def gen10BackupVNFISequence(self, SFCLength=1):
        # hard-code function
        vnfiSequence = []
        for index in range(SFCLength):
            vnfiSequence.append([])
            for iN in range(1):
                server = Server("ens3", SFF1_DATAPATH_IP, SERVER_TYPE_NFVI)
                server.setServerID(SFF1_SERVERID)
                server.setControlNICIP(SFF1_CONTROLNIC_IP)
                server.setControlNICMAC(SFF1_CONTROLNIC_MAC)
                server.setDataPathNICMAC(SFF1_DATAPATH_MAC)
                vnfi = VNFI(VNF_TYPE_FORWARD, vnfType=VNF_TYPE_FORWARD,
                    vnfiID=uuid.uuid1(), node=server)
                vnfiSequence[index].append(vnfi)
        return vnfiSequence

    def genUniDirection10BackupForwardingPathSet(self):
        # please ref /sam/base/path.py
        # This function generate a sfc forwarding path for sfc "ingress->L2Forwarding->egress"
        # The primary forwarding path has two stage, the first stage is "ingress->L2Forwarding",
        # the second stage is "L2Forwarding->egress".
        # Each stage is a list of layeredNodeIDTuple which format is (stageIndex, nodeID)
        primaryForwardingPath = {
                                    1:[
                                        [(0,10001),(0,0),(0,256),(0,768),(0,10771)], # (stageIndex, nodeID)
                                        [(1,10771),(1,768),(1,256),(1,0),(1,10001)]
                                    ]
                                }
        mappingType = MAPPING_TYPE_INTERFERENCE # This is your mapping algorithm type, e.g. interference-aware mapping algorithm
        backupForwardingPath = {}   # you don't need to care about backupForwardingPath
        return ForwardingPathSet(primaryForwardingPath,mappingType,
                                    backupForwardingPath)