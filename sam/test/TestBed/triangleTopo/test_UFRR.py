#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
import time
import logging

import pytest
from ryu.controller import dpset

from sam.ryu.topoCollector import TopoCollector
from sam.base.slo import *
from sam.base.server import *
from sam.base.command import *
from sam.base.shellProcessor import ShellProcessor
from sam.test.testBase import *
from sam.test.fixtures.vnfControllerStub import *
from sam.test.FRR.testFRR import TestFRR

logging.basicConfig(level=logging.INFO)
logging.getLogger("pika").setLevel(logging.WARNING)

TESTER_SERVER_DATAPATH_MAC = "18:66:da:85:f9:ed"
OUTTER_CLIENT_IP = "1.1.1.1"
WEBSITE_REAL_IP = "3.3.3.3"

CLASSIFIER_DATAPATH_IP = "2.2.0.36"
CLASSIFIER_DATAPATH_MAC = "00:1b:21:c0:8f:ae"
CLASSIFIER_CONTROL_IP = "192.168.0.194"
CLASSIFIER_SERVERID = 10001

SFF1_DATAPATH_IP = "2.2.0.69"
SFF1_DATAPATH_MAC = "b8:ca:3a:65:f7:fa"
SFF1_CONTROLNIC_IP = "192.168.8.17"
SFF1_CONTROLNIC_MAC = "b8:ca:3a:65:f7:f8"
SFF1_SERVERID = 10003

SFF2_DATAPATH_IP = "2.2.0.71"
SFF2_DATAPATH_MAC = "ec:f4:bb:da:39:45"
SFF2_CONTROLNIC_IP = "192.168.8.18"
SFF2_CONTROLNIC_MAC = "ec:f4:bb:da:39:44"
SFF2_SERVERID = 10004

SFF3_DATAPATH_IP = "2.2.0.99"
SFF3_DATAPATH_MAC = "00:1b:21:c0:8f:98"
SFF3_CONTROLNIC_IP = "192.168.0.173"
SFF3_CONTROLNIC_MAC = "18:66:da:85:1c:c3"
SFF3_SERVERID = 10005


class TestUFRRClass(TestFRR):
    @pytest.fixture(scope="function")
    def setup_addUniSFCI(self):
        # setup
        self.sP = ShellProcessor()
        self.clearQueue()
        self.killAllModule()

        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genUniDirectionSFC(classifier)
        self.sfci = self.genUniDirection12BackupSFCI()

        self.mediator = MediatorStub()
        self.addSFCCmd = self.mediator.genCMDAddSFC(self.sfc)
        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.sfci)
        self.delSFCICmd = self.mediator.genCMDDelSFCI(self.sfc, self.sfci)

        self._messageAgent = MessageAgent()

        self.runClassifierController()
        self.addSFCI2Classifier()

        self.runSFFController()
        self.addSFCI2SFF()

        # self.vC = VNFControllerStub()
        # time.sleep(5)
        self.runVNFController()
        self.addVNFI2Server()

        yield
        # teardown
        self.delVNFI4Server()
        self.delSFCI2SFF()
        self.delSFCI2Classifier()
        self.killClassifierController()
        self.killSFFController()
        self.killVNFController()

    def addVNFI2Server(self):
        self.sendCmd(VNF_CONTROLLER_QUEUE,
            MSG_TYPE_VNF_CONTROLLER_CMD , self.addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def delVNFI4Server(self):
        logging.warning("Deleting VNFI")
        self.sendCmd(VNF_CONTROLLER_QUEUE,
            MSG_TYPE_VNF_CONTROLLER_CMD , self.delSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

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
            'match': {'srcIP': "*",'dstIP': WEBSITE_REAL_IP,
                'srcPort': "*",'dstPort': "*",'proto': "*"},
            'egress': classifier,
            'destination': {"IPv4":WEBSITE_REAL_IP}
        }
        directions = [direction1]
        slo = SLO(latencyBound=35, throughput=10)
        return SFC(sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
            backupInstanceNumber, applicationType, directions, slo=slo)

    def gen12BackupVNFISequence(self, SFCLength=1):
        # hard-code function
        vnfiSequence = []
        for index in range(SFCLength):
            vnfiSequence.append([])

            server = Server("ens3", SFF1_DATAPATH_IP, SERVER_TYPE_NFVI)
            server.setServerID(SFF1_SERVERID)
            server.setControlNICIP(SFF1_CONTROLNIC_IP)
            server.setControlNICMAC(SFF1_CONTROLNIC_MAC)
            server.setDataPathNICMAC(SFF1_DATAPATH_MAC)
            vnfi = VNFI(vnfID=VNF_TYPE_FORWARD, vnfType=VNF_TYPE_FORWARD, 
                vnfiID=uuid.uuid1(), node=server)
            vnfiSequence[index].append(vnfi)

            server = Server("ens3", SFF2_DATAPATH_IP, SERVER_TYPE_NFVI)
            server.setServerID(SFF2_SERVERID)
            server.setControlNICIP(SFF2_CONTROLNIC_IP)
            server.setControlNICMAC(SFF2_CONTROLNIC_MAC)
            server.setDataPathNICMAC(SFF2_DATAPATH_MAC)
            vnfi = VNFI(vnfID=VNF_TYPE_FORWARD, vnfType=VNF_TYPE_FORWARD,
                vnfiID=uuid.uuid1(), node=server)
            vnfiSequence[index].append(vnfi)

            server = Server("ens3", SFF3_DATAPATH_IP, SERVER_TYPE_NFVI)
            server.setServerID(SFF3_SERVERID)
            server.setControlNICIP(SFF3_CONTROLNIC_IP)
            server.setControlNICMAC(SFF3_CONTROLNIC_MAC)
            server.setDataPathNICMAC(SFF3_DATAPATH_MAC)
            vnfi = VNFI(vnfID=VNF_TYPE_FORWARD, vnfType=VNF_TYPE_FORWARD,
                vnfiID=uuid.uuid1(), node=server)
            vnfiSequence[index].append(vnfi)

        return vnfiSequence

    # @pytest.mark.skip(reason='Temporarly')
    def test_UFRRAddUniSFCI(self, setup_addUniSFCI):
        logging.info("You need start ryu-manager and mininet manually!"
            "Then press any key to continue!")
        raw_input()

        self.addSFC2NetworkController()
        self.addSFCI2NetworkController()

        logging.info("Please input any key to test "
            "server software failure\n"
            "After the test, "
            "Press any key to quit!")
        raw_input()
        self.sendHandleServerSoftwareFailureCmd()

        logging.info("Please input mode 0 into mininet\n"
            "After the test, "
            "Press any key to quit!")
        raw_input()

    def addSFC2NetworkController(self):
        # exercise: mapping SFC
        self.addSFCCmd.cmdID = uuid.uuid1()
        self.sendCmd(NETWORK_CONTROLLER_QUEUE,
            MSG_TYPE_NETWORK_CONTROLLER_CMD,
            self.addSFCCmd)

        # verify
        logging.info("Start listening on mediator queue")
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCCmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def addSFCI2NetworkController(self):
        # exercise: mapping SFCI
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(NETWORK_CONTROLLER_QUEUE,
            MSG_TYPE_NETWORK_CONTROLLER_CMD,
            self.addSFCICmd)

        # verify
        logging.info("Start listening on mediator queue")
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
