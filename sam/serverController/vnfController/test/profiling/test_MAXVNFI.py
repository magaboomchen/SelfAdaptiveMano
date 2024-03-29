#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid

import pytest
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.routingMorphic import IPV4_ROUTE_PROTOCOL

from sam.base.vnf import VNFI, VNF_TYPE_FW
from sam.base.compatibility import screenInput
from sam.base.acl import ACLTable, ACLTuple, ACL_ACTION_ALLOW, ACL_PROTO_TCP
from sam.base.messageAgent import VNF_CONTROLLER_QUEUE, MSG_TYPE_VNF_CONTROLLER_CMD, \
    SFF_CONTROLLER_QUEUE, MSG_TYPE_SFF_CONTROLLER_CMD, MEDIATOR_QUEUE
from sam.base.server import Server, SERVER_TYPE_NORMAL
from sam.serverController.serverManager.serverManager import SERVERID_OFFSET
from sam.base.command import CMD_STATE_SUCCESSFUL
from sam.base.shellProcessor import ShellProcessor
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.test.testBase import TestBase, OUTTER_CLIENT_IP, WEBSITE_REAL_IP

TESTER_SERVER_DATAPATH_IP = "2.2.0.36"
TESTER_SERVER_DATAPATH_MAC = "00:1b:21:c0:8f:ae"

SFF0_DATAPATH_IP = "2.2.0.38"
SFF0_DATAPATH_MAC = "00:1b:21:c0:8f:98"
SFF0_CONTROLNIC_IP = "192.168.0.173"
SFF0_CONTROLNIC_MAC = "18:66:da:85:1c:c3"

# fast click doesn't support NUMA architecture!
MAX_SFCI = 5


class TestVNFSFCIAdderClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_addSFCI(self):
        # setup
        logConfigur = LoggerConfigurator(__name__,
            './log', 'testVNFSFCIAdder.log', level='debug')
        self.logger = logConfigur.getLogger()

        self.sP = ShellProcessor()
        self.clearQueue()
        self.killAllModule()

        # classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        classifier = None
        self.mediator = MediatorStub()
        # self.server = self.genTesterServer(TESTER_SERVER_DATAPATH_IP,
        #     TESTER_SERVER_DATAPATH_MAC)

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
        for sfciIndex in range(MAX_SFCI):
            self.sfci = self.genBiDirection10BackupSFCI()
            self.sfciList.append(self.sfci)

    def genAddSFCICmdList(self):
        self.addSFCICmdList = []
        for sfciIndex in range(MAX_SFCI):
            sfci = self.sfciList[sfciIndex]
            addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, sfci)
            self.logger.info("sfci id: {0}".format(sfci.sfciID))
            self.addSFCICmdList.append(addSFCICmd)

    def gen10BackupVNFISequence(self, SFCLength=1):
        # hard-code function
        self.logger.info("use override function")
        vnfiSequence = []
        for index in range(SFCLength):
            vnfiSequence.append([])
            for iN in range(1):
                server = Server("ens3", SFF0_DATAPATH_IP, SERVER_TYPE_NORMAL)
                server.setServerID(SERVERID_OFFSET + 1)
                server.setControlNICIP(SFF0_CONTROLNIC_IP)
                server.setControlNICMAC(SFF0_CONTROLNIC_MAC)
                server.setDataPathNICMAC(SFF0_DATAPATH_MAC)
                server.updateResource()
                vnfi = VNFI(VNF_TYPE_FW, vnfType=VNF_TYPE_FW, 
                    vnfiID=uuid.uuid1(), node=server, config=self.genTestIPv4FWRules())
                # vnfi = VNFI(VNF_TYPE_FORWARD, vnfType=VNF_TYPE_FORWARD, 
                #     vnfiID=uuid.uuid1(), node=server)
                vnfi.maxCPUNum = 1
                vnfiSequence[index].append(vnfi)
        return vnfiSequence

    def genTestIPv4FWRules(self):
        entry1 = ACLTuple(ACL_ACTION_ALLOW, proto=ACL_PROTO_TCP, srcAddr=OUTTER_CLIENT_IP, dstAddr=WEBSITE_REAL_IP, 
            srcPort=(1234, 1234), dstPort=(80, 80))
        entry2 = ACLTuple(ACL_ACTION_ALLOW, proto=ACL_PROTO_TCP, srcAddr=WEBSITE_REAL_IP, dstAddr=OUTTER_CLIENT_IP,
            srcPort=(80, 80), dstPort=(1234, 1234))
        entry3 = ACLTuple(ACL_ACTION_ALLOW)
        aclT = ACLTable()
        aclT.addRules(entry1, IPV4_ROUTE_PROTOCOL)
        aclT.addRules(entry2, IPV4_ROUTE_PROTOCOL)
        aclT.addRules(entry3, IPV4_ROUTE_PROTOCOL)
        return aclT

    def test_addSFCI(self, setup_addSFCI):
        # exercise
        self.logger.info("exercise")
        self.addSFCI2SFF()
        self.addVNFI2Server()

        # verifiy
        self.logger.info("please start performance profiling" \
            "after profiling, press any key to quit.")
        screenInput()

    def addSFCI2SFF(self):
        self.logger.info("setup add SFCI to sff")
        for sfciIndex in range(MAX_SFCI):
            addSFCICmd = self.addSFCICmdList[sfciIndex]
            addSFCICmd.cmdID = uuid.uuid1()
            self.sendCmd(SFF_CONTROLLER_QUEUE,
                MSG_TYPE_SFF_CONTROLLER_CMD , addSFCICmd)
            cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
            assert cmdRply.cmdID == addSFCICmd.cmdID
            assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def addVNFI2Server(self):
        for sfciIndex in range(MAX_SFCI):
            addSFCICmd = self.addSFCICmdList[sfciIndex]
            addSFCICmd.cmdID = uuid.uuid1()
            self.sendCmd(VNF_CONTROLLER_QUEUE,
                MSG_TYPE_VNF_CONTROLLER_CMD , addSFCICmd)
            cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
            assert cmdRply.cmdID == addSFCICmd.cmdID
            assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def delVNFI4Server(self):
        self.logger.warning("Deleting VNFI")
        for sfciIndex in range(MAX_SFCI):
            sfci = self.sfciList[sfciIndex]
            delSFCICmd = self.mediator.genCMDDelSFCI(self.sfc, sfci)
            self.sendCmd(VNF_CONTROLLER_QUEUE, MSG_TYPE_VNF_CONTROLLER_CMD, delSFCICmd)
            cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
            assert cmdRply.cmdID == delSFCICmd.cmdID
            assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
