#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.sfc import *
from sam.base.vnf import *
from sam.base.server import *
from sam.serverController.classifierController import *
from sam.base.command import *
from sam.base.socketConverter import *
from sam.base.shellProcessor import ShellProcessor
from sam.test.fixtures.mediatorStub import *
from sam.test.fixtures.vnfControllerStub import *
from sam.test.testBase import *

import pytest
from scapy.all import *

MANUAL_TEST = True

TESTER_SERVER_DATAPATH_IP = "192.168.124.1"
TESTER_SERVER_DATAPATH_MAC = "fe:54:00:42:26:44"

class TestSFFSFCIDeleterClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_delSFCI(self):
        # setup
        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genBiDirectionSFC(classifier)
        self.sfci = self.genBiDirection10BackupSFCI()
        self.mediator = MediatorStub()
        self.sP = ShellProcessor()
        self.sP.runShellCommand("sudo rabbitmqctl purge_queue MEDIATOR_QUEUE")
        self.sP.runShellCommand(
                "sudo rabbitmqctl purge_queue SFF_CONTROLLER_QUEUE")
        self.server = self.genTesterServer(TESTER_SERVER_DATAPATH_IP,
            TESTER_SERVER_DATAPATH_MAC)
        self.vC = VNFControllerStub()
        self.runSFFController()
        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.sfci)
        self.sendCmd(SFF_CONTROLLER_QUEUE,
            MSG_TYPE_SSF_CONTROLLER_CMD , self.addSFCICmd)
        yield
        # teardown
        self.killSFFController()

    def runSFFController(self):
        filePath = "~/HaoChen/Project/SelfAdaptiveMano/sam/serverController/sffController/sffControllerCommandAgent.py"
        self.sP.runPythonScript(filePath)

    def killSFFController(self):
        self.sP.killPythonScript("sffControllerCommandAgent.py")

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_delSFCI(self, setup_delSFCI):
        # exercise
        self.verifyAddSFCICmdRply()
        self.delSFCICmd = self.mediator.genCMDDelSFCI(self.sfc, self.sfci)
        self.sendCmd(SFF_CONTROLLER_QUEUE,
            MSG_TYPE_SSF_CONTROLLER_CMD , self.delSFCICmd)

        # verify
        self.verifyDelSFCICmdRply()

    def verifyAddSFCICmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def verifyDelSFCICmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL