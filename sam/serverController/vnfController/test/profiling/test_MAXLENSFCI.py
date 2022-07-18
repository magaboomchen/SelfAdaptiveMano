#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid
import logging

import pytest

from sam.base.compatibility import screenInput
from sam.base.server import Server, SERVER_TYPE_NORMAL
from sam.base.vnf import VNF_TYPE_FW, VNFI, VNF_TYPE_FORWARD
from sam.serverController.serverManager.serverManager import SERVERID_OFFSET
from sam.base.acl import ACLTuple, ACL_ACTION_ALLOW, ACL_PROTO_TCP, \
    ACL_ACTION_DENY
from sam.base.command import CMD_STATE_SUCCESSFUL
from sam.base.messageAgent import VNF_CONTROLLER_QUEUE, MSG_TYPE_VNF_CONTROLLER_CMD, \
    SFF_CONTROLLER_QUEUE, MSG_TYPE_SFF_CONTROLLER_CMD, MEDIATOR_QUEUE
from sam.base.shellProcessor import ShellProcessor
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.test.testBase import TestBase, CLASSIFIER_DATAPATH_IP, WEBSITE_REAL_IP, \
    TESTER_SERVER_DATAPATH_MAC, OUTTER_CLIENT_IP

MANUAL_TEST = True
TESTER_SERVER_DATAPATH_IP = "2.2.0.36"
TESTER_SERVER_DATAPATH_MAC = "f4:e9:d4:a3:53:a0"

SFF0_DATAPATH_IP = "2.2.0.38"
SFF0_DATAPATH_MAC = "00:1b:21:c0:8f:98"
SFF0_CONTROLNIC_IP = "192.168.0.173"
SFF0_CONTROLNIC_MAC = "18:66:da:85:1c:c3"

MAX_SFCI_NUM = 1

logging.basicConfig(level=logging.INFO)
logging.getLogger("pika").setLevel(logging.WARNING)


class TestVNFSFCIAdderClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_addSFCI(self):
        # setup
        self.sP = ShellProcessor()
        self.clearQueue()
        self.killAllModule()

        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.mediator = MediatorStub()
        self.server = self.genTesterServer(TESTER_SERVER_DATAPATH_IP,
            TESTER_SERVER_DATAPATH_MAC)

        self.runSFFController()
        self.runVNFController()

        self.sfc = self.genBiDirectionSFC(classifier)

        self.genSFCIList()
        self.genAddSFCICmdList()

        yield
        # teardown
        self.delVNFI4Server()
        self.killSFFController()
        self.killVNFController()

    def genSFCIList(self):
        self.sfciList = []
        for sfciIndex in range(MAX_SFCI_NUM):
            self.sfci = self.genBiDirection10BackupSFCI()
            self.sfciList.append(self.sfci)

    def genAddSFCICmdList(self):
        self.addSFCICmdList = []
        for sfciIndex in range(MAX_SFCI_NUM):
            sfci = self.sfciList[sfciIndex]
            addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, sfci)
            logging.info("sfci id: {0}".format(sfci.sfciID))
            self.addSFCICmdList.append(addSFCICmd)

    def gen10BackupVNFISequence(self, SFCLength=7):
        # hard-code function
        logging.info("use override function")
        vnfiSequence = []

        server = Server("ens3", SFF0_DATAPATH_IP, SERVER_TYPE_NORMAL)
        server.setServerID(SERVERID_OFFSET + 1)
        server.setControlNICIP(SFF0_CONTROLNIC_IP)
        server.setControlNICMAC(SFF0_CONTROLNIC_MAC)
        server.setDataPathNICMAC(SFF0_DATAPATH_MAC)
        server.updateResource()

        vnfi = VNFI(VNF_TYPE_FORWARD, vnfType=VNF_TYPE_FORWARD, 
            vnfiID=uuid.uuid1(), node=server)
        vnfi.maxCPUNum = 1
        index = 0
        vnfiSequence.append([])
        vnfiSequence[index].append(vnfi)

        config = {}
        config['ACL'] = self.genTestIPv4FWRules()
        vnfi = VNFI(VNF_TYPE_FW, vnfType=VNF_TYPE_FW, 
            vnfiID=uuid.uuid1(), config=config, node=server)
        vnfi.maxCPUNum = 1
        index = 1
        vnfiSequence.append([])
        vnfiSequence[index].append(vnfi)

        # vnfi = VNFI(VNF_TYPE_IDS, vnfType=VNF_TYPE_IDS, 
        #     vnfiID=uuid.uuid1(), node=server)
        # vnfi.maxCPUNum = 1
        # index = 2
        # vnfiSequence.append([])
        # vnfiSequence[index].append(vnfi)

        # vnfi = VNFI(VNF_TYPE_MONITOR, vnfType=VNF_TYPE_MONITOR, 
        #     vnfiID=uuid.uuid1(), node=server)
        # vnfi.maxCPUNum = 1
        # index = 3
        # vnfiSequence.append([])
        # vnfiSequence[index].append(vnfi)

        # vnfi = VNFI(VNF_TYPE_LB, vnfType=VNF_TYPE_LB, 
        #     vnfiID=uuid.uuid1(), node=server)
        # vnfi.maxCPUNum = 1
        # index = 4
        # vnfiSequence.append([])
        # vnfiSequence[index].append(vnfi)

        # vnfi = VNFI(VNF_TYPE_NAT, vnfType=VNF_TYPE_NAT, 
        #     vnfiID=uuid.uuid1(), node=server)
        # vnfi.maxCPUNum = 1
        # index = 5
        # vnfiSequence.append([])
        # vnfiSequence[index].append(vnfi)

        # vnfi = VNFI(VNF_TYPE_VPN, vnfType=VNF_TYPE_VPN, 
        #     vnfiID=uuid.uuid1(), node=server)
        # vnfi.maxCPUNum = 1
        # index = 6
        # vnfiSequence.append([])
        # vnfiSequence[index].append(vnfi)

        logging.info("vnfiSequence: {0}".format(vnfiSequence))
        return vnfiSequence

    def genTestIPv4FWRules(self):
        rules = []
        rules.append(ACLTuple(ACL_ACTION_ALLOW, proto=ACL_PROTO_TCP, srcAddr=OUTTER_CLIENT_IP, dstAddr=WEBSITE_REAL_IP, 
            srcPort=(1234, 1234), dstPort=(80, 80)))
        rules.append(ACLTuple(ACL_ACTION_ALLOW, proto=ACL_PROTO_TCP, srcAddr=WEBSITE_REAL_IP, dstAddr=OUTTER_CLIENT_IP,
            srcPort=(80, 80), dstPort=(1234, 1234)))
        rules.append(ACLTuple(ACL_ACTION_DENY))
        return rules

    def test_addSFCI(self, setup_addSFCI):
        # exercise
        logging.info("exercise")
        self.addSFCI2SFF()
        self.addVNFI2Server()

        # verifiy
        logging.info("please start performance profiling" \
            "after profiling, press any key to quit.")
        screenInput()

    def addSFCI2SFF(self):
        logging.info("setup add SFCI to sff")
        for sfciIndex in range(MAX_SFCI_NUM):
            addSFCICmd = self.addSFCICmdList[sfciIndex]
            addSFCICmd.cmdID = uuid.uuid1()
            self.sendCmd(SFF_CONTROLLER_QUEUE,
                MSG_TYPE_SFF_CONTROLLER_CMD , addSFCICmd)
            cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
            assert cmdRply.cmdID == addSFCICmd.cmdID
            assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def addVNFI2Server(self):
        for sfciIndex in range(MAX_SFCI_NUM):
            addSFCICmd = self.addSFCICmdList[sfciIndex]
            addSFCICmd.cmdID = uuid.uuid1()
            self.sendCmd(VNF_CONTROLLER_QUEUE,
                MSG_TYPE_VNF_CONTROLLER_CMD , addSFCICmd)
            cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
            assert cmdRply.cmdID == addSFCICmd.cmdID
            assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def delVNFI4Server(self):
        logging.warning("Deleting VNFI")
        for sfciIndex in range(MAX_SFCI_NUM):
            sfci = self.sfciList[sfciIndex]
            delSFCICmd = self.mediator.genCMDDelSFCI(self.sfc, sfci)
            self.sendCmd(VNF_CONTROLLER_QUEUE, MSG_TYPE_VNF_CONTROLLER_CMD, delSFCICmd)
            cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
            assert cmdRply.cmdID == delSFCICmd.cmdID
            assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
