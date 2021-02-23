#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging
from scapy.all import *
import time

import pytest

from sam.base import server
from sam.base.sfc import *
from sam.base.vnf import *
from sam.base.server import *
from sam.base.command import *
from sam.base.socketConverter import *
from sam.base.shellProcessor import ShellProcessor
from sam.test.fixtures.mediatorStub import *
from sam.test.fixtures.vnfControllerStub import *
from sam.test.testBase import *
from sam.serverController.classifierController import *

MANUAL_TEST = True
TESTER_SERVER_DATAPATH_IP = "2.2.0.36"
TESTER_SERVER_DATAPATH_MAC = "00:1b:21:c0:8f:ae"

SFF0_DATAPATH_IP = "2.2.0.38"
SFF0_DATAPATH_MAC = "00:1b:21:c0:8f:98"
SFF0_CONTROLNIC_IP = "192.168.0.173"
SFF0_CONTROLNIC_MAC = "18:66:da:85:1c:c3"

# fast click doesn't support NUMA architecture!
MAX_SFCI = 5

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
        for sfciIndex in range(MAX_SFCI):
            self.sfci = self.genBiDirection10BackupSFCI()
            self.sfciList.append(self.sfci)

    def genAddSFCICmdList(self):
        self.addSFCICmdList = []
        for sfciIndex in range(MAX_SFCI):
            sfci = self.sfciList[sfciIndex]
            addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, sfci)
            logging.info("sfci id: {0}".format(sfci.sfciID))
            self.addSFCICmdList.append(addSFCICmd)

    def gen10BackupVNFISequence(self, SFCLength=1):
        # hard-code function
        logging.info("use override function")
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
                vnfi = VNFI(VNF_TYPE_FORWARD, vnfType=VNF_TYPE_FORWARD, 
                    vnfiID=uuid.uuid1(), node=server)
                vnfi.maxCPUNum = 1
                vnfiSequence[index].append(vnfi)
        return vnfiSequence

    def test_addSFCI(self, setup_addSFCI):
        # exercise
        logging.info("exercise")
        self.addSFCI2SFF()
        self.addVNFI2Server()

        # verifiy
        logging.info("please start performance profiling" \
            "after profiling, press any key to quit.")
        raw_input()

    def addSFCI2SFF(self):
        logging.info("setup add SFCI to sff")
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
            # logging.info("press any key to continue place vnfi")
            # raw_input()
            addSFCICmd = self.addSFCICmdList[sfciIndex]
            addSFCICmd.cmdID = uuid.uuid1()
            self.sendCmd(VNF_CONTROLLER_QUEUE,
                MSG_TYPE_VNF_CONTROLLER_CMD , addSFCICmd)
            cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
            assert cmdRply.cmdID == addSFCICmd.cmdID
            assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def delVNFI4Server(self):
        logging.warning("Deleting VNFI")
        for sfciIndex in range(MAX_SFCI):
            sfci = self.sfciList[sfciIndex]
            delSFCICmd = self.mediator.genCMDDelSFCI(self.sfc, sfci)
            self.sendCmd(VNF_CONTROLLER_QUEUE, MSG_TYPE_VNF_CONTROLLER_CMD, delSFCICmd)
            cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
            assert cmdRply.cmdID == delSFCICmd.cmdID
            assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
