#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid
import time

import pytest

from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.messageAgent import VNF_CONTROLLER_QUEUE, MSG_TYPE_VNF_CONTROLLER_CMD, \
    SFF_CONTROLLER_QUEUE, MSG_TYPE_SFF_CONTROLLER_CMD, MEDIATOR_QUEUE
from sam.base.vnf import VNFI, VNF_TYPE_FORWARD
from sam.base.server import Server, SERVER_TYPE_NORMAL
from sam.serverController.serverManager.serverManager import SERVERID_OFFSET
from sam.base.command import CMD_STATE_SUCCESSFUL
from sam.base.shellProcessor import ShellProcessor
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.test.testBase import TestBase, CLASSIFIER_DATAPATH_IP

TESTER_SERVER_DATAPATH_IP = "2.2.0.199"
TESTER_SERVER_DATAPATH_MAC = "52:54:00:a8:b0:a1"

SFF0_DATAPATH_IP = "2.2.0.200"
SFF0_DATAPATH_MAC = "52:54:00:5a:14:f0"
SFF0_CONTROLNIC_IP = "192.168.0.201"
SFF0_CONTROLNIC_MAC = "52:54:00:1f:51:12"


class TestVNFSFCIDeleterClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_delSFCI(self):
        # setup
        logConfigur = LoggerConfigurator(__name__,
            './log', 'testVNFSFCIDeleterClass.log',
            level='debug')
        self.logger = logConfigur.getLogger()

        self.sP = ShellProcessor()
        self.clearQueue()
        self.killAllModule()

        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genBiDirectionSFC(classifier)
        self.sfci = self.genBiDirection10BackupSFCI()
        self.mediator = MediatorStub()

        self.runSFFController()
        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.sfci)
        self.addSFCI2SFF()
        self.runVNFController()

        yield

        self.killSFFController()
        self.killVNFController()
      
    def gen10BackupVNFISequence(self, SFCLength=1):
        # hard-code function
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
                vnfiSequence[index].append(vnfi)
        return vnfiSequence

    def addSFCI2SFF(self):
        self.logger.info("setup add SFCI to sff")
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SFF_CONTROLLER_QUEUE,
            MSG_TYPE_SFF_CONTROLLER_CMD , self.addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def test_delSFCI(self, setup_delSFCI):
        # exercise
        self.logger.info("exercise")
        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.sfci)
        self.sendCmd(VNF_CONTROLLER_QUEUE,
            MSG_TYPE_VNF_CONTROLLER_CMD , self.addSFCICmd)
        addCmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert addCmdRply.cmdID == self.addSFCICmd.cmdID
        assert addCmdRply.cmdState == CMD_STATE_SUCCESSFUL

        self.logger.info("Finish adding sfci.")
        self.logger.info("Wait for deleting sfci.")

        time.sleep(10)
        self.logger.info("Deleting sfci.")
        self.delSFCICmd = self.mediator.genCMDDelSFCI(self.sfc, self.sfci)
        self.sendCmd(VNF_CONTROLLER_QUEUE,
            MSG_TYPE_VNF_CONTROLLER_CMD, self.delSFCICmd)
        delCmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert delCmdRply.cmdID == self.delSFCICmd.cmdID
        assert delCmdRply.cmdState == CMD_STATE_SUCCESSFUL