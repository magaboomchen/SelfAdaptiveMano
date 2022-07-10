#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid
import logging
from sam.base.command import CMD_STATE_SUCCESSFUL

from sam.base.messageAgent import MEDIATOR_QUEUE, MSG_TYPE_P4CONTROLLER_CMD, P4CONTROLLER_QUEUE, TURBONET_ZONE
from sam.base.shellProcessor import ShellProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.sfc import SFCI
from sam.base.path import MAPPING_TYPE_MMLPSFC, ForwardingPathSet
from sam.base.test.fixtures.srv6MorphicDict import srv6MorphicDictTemplate
from sam.base.vnf import VNFI, VNF_TYPE_FORWARD
from sam.base.switch import SWITCH_TYPE_DCNGATEWAY, SWITCH_TYPE_NPOP, Switch
from sam.test.fixtures.measurementStub import MeasurementStub
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.test.integrate.intTestBase import IntTestBaseClass
from sam.test.testBase import DCN_GATEWAY_IP

MANUAL_TEST = True

SFF1_DATAPATH_IP = "2.2.1.193"
SFF1_DATAPATH_MAC = "b8:ca:3a:65:f7:fa" # ignore this
SFF1_CONTROLNIC_IP = "192.168.8.17" # ignore this
SFF1_CONTROLNIC_MAC = "b8:ca:3a:65:f7:f8"   # ignore this
SFF1_SERVERID = 10001

SWITCH_SFF1_SWITCHID = 20
SWITCH_SFF1_LANIP = "2.2.2.128" # prefix length is /27
SWITCH_SFF2_SWITCHID = 21
SWITCH_SFF2_LANIP = "2.2.3.0" # prefix length is /27


class TestP4ControllerBase(IntTestBaseClass):
    MAXSFCIID = 0
    sfciCounter = 0
    logging.getLogger("pika").setLevel(logging.WARNING)

    def common_setup(self):
        logConfigur = LoggerConfigurator(__name__, './log',
                                            'testP4ControllerBase.log',
                                            level='debug')
        self.logger = logConfigur.getLogger()
        self.logger.setLevel(logging.DEBUG)

        # setup
        self.sP = ShellProcessor()
        self.cleanLog()
        self.clearQueue()
        self.killAllModule()
        self.mediator = MediatorStub()
        self.measurer = MeasurementStub()

        self.sfcList = []
        self.sfciList = []

        classifier = Switch(0, SWITCH_TYPE_DCNGATEWAY, DCN_GATEWAY_IP,
                                                    programmable=True)

        sfc1 = self.genLargeBandwidthSFC(classifier, zone=TURBONET_ZONE)
        sfci1 = self.genUniDirection10BackupP4NFVISFCI(sfcLength=2)    # genLargeBandwidthSFCI()

        sfc3 = self.genLowLatencySFC(classifier, zone=TURBONET_ZONE)
        sfci3 = self.genUniDirection10BackupP4NFVISFCI(sfcLength=1)    # genLowLatencySFCI()

        sfc4 = self.genLargeConnectionSFC(classifier, zone=TURBONET_ZONE)
        sfci4 = self.genUniDirection10BackupP4NFVISFCI(sfcLength=1)     # genLargeConnectionSFCI()

        self.sfcList = [sfc1, sfc3, sfc4]
        self.sfciList = [sfci1, sfci3, sfci4]

    def genUniDirection10BackupP4NFVISFCI(self, mappedVNFISeq=True, sfcLength=1):
        if mappedVNFISeq:
            vnfiSequence = self.gen10BackupP4VNFISequence(sfcLength)
        else:
            vnfiSequence = None
        return SFCI(self.assignSFCIID(), vnfiSequence, None,
            self.genUniDirection10BackupP4BasedForwardingPathSet(sfcLength))

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

    def genUniDirection10BackupP4BasedForwardingPathSet(self, sfciLength=1):
        # please ref /sam/base/path.py
        # This function generate a sfc forwarding path for sfc "ingress->L2Forwarding->egress"
        # The primary forwarding path has two stage, the first stage is "ingress->L2Forwarding",
        # the second stage is "L2Forwarding->egress".
        # Each stage is a list of layeredNodeIDTuple which format is (stageIndex, nodeID)
        if sfciLength == 1:
            d1FP = [
                    [(0,0),(0,8),(0,16),(0,SWITCH_SFF1_SWITCHID)], # (stageIndex, nodeID)
                    [(1,SWITCH_SFF1_SWITCHID),(1,16),(1,8),(1,0)]   # Note that may be a serverID ocurred in path!
                ]
        elif sfciLength == 2:
            d1FP = [
                    [(0,0),(0,8),(0,16),(0,SWITCH_SFF1_SWITCHID)],
                    [(1,SWITCH_SFF1_SWITCHID),(1,SWITCH_SFF1_SWITCHID)],
                    [(2,SWITCH_SFF1_SWITCHID),(2,16),(2,8),(2,0)]
                ]
        elif sfciLength == 3:
            d1FP = [
                    [(0,0),(0,8),(0,16),(0,SWITCH_SFF1_SWITCHID)],
                    [(1,SWITCH_SFF1_SWITCHID),(1,SWITCH_SFF1_SWITCHID)],
                    [(2,SWITCH_SFF1_SWITCHID),(2,SWITCH_SFF1_SWITCHID)],
                    [(3,SWITCH_SFF1_SWITCHID),(3,16) ,(3,8), (3,0)]
                ]
        else:
            raise ValueError("Unimplement sfci length!")
        primaryForwardingPath = {1:d1FP}   
        mappingType = MAPPING_TYPE_MMLPSFC # This is your mapping algorithm type
        backupForwardingPath = {}   # you don't need to care about backupForwardingPath
        return ForwardingPathSet(primaryForwardingPath, mappingType,
                                    backupForwardingPath)

    def exerciseAddSFCAndSFCI(self):
        for idx in [0,1,2]:
            logging.info("test idx {0}".format(idx))
            # exercise
            self.addSFCCmd = self.mediator.genCMDAddSFC(self.sfcList[idx])
            self.sendCmd(P4CONTROLLER_QUEUE, MSG_TYPE_P4CONTROLLER_CMD,
                                                    self.addSFCCmd)

            # verify
            self.verifyAddSFCCmdRply()

            # exercise
            self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfcList[idx],
                                                        self.sfciList[idx])
            self.sendCmd(P4CONTROLLER_QUEUE, MSG_TYPE_P4CONTROLLER_CMD,
                                                self.addSFCICmd)

            # verify
            self.verifyAddSFCICmdRply()

    def verifyAddSFCCmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCCmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        assert cmdRply.attributes['zone'] == TURBONET_ZONE

    def verifyAddSFCICmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        assert cmdRply.attributes['zone'] == TURBONET_ZONE

    def verifyDelSFCICmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        assert cmdRply.attributes['zone'] == TURBONET_ZONE
