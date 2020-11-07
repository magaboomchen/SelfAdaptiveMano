#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging
from scapy.all import *

import pytest

from sam.base.sfc import *
from sam.base.vnf import *
from sam.base.server import *
from sam.base.command import *
from sam.base.socketConverter import *
from sam.base.shellProcessor import ShellProcessor
from sam.test.fixtures.mediatorStub import *
from sam.test.testBase import *
from sam.serverController.classifierController import *
from sam.serverController.classifierController import classifierControllerCommandAgent

MANUAL_TEST = True

TESTER_SERVER_DATAPATH_IP = "192.168.123.1"
TESTER_SERVER_DATAPATH_MAC = "fe:54:00:05:4d:7d"

logging.basicConfig(level=logging.INFO)

class TestSFCIDeleterClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_addSFCI(self):
        # setup
        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genBiDirectionSFC(classifier)
        self.sfci = self.genBiDirection10BackupSFCI()
        self.mediator = MediatorStub()
        self.sP = ShellProcessor()
        self.sP.runShellCommand("sudo rabbitmqctl purge_queue MEDIATOR_QUEUE")
        self.sP.runShellCommand("sudo rabbitmqctl purge_queue SERVER_CLASSIFIER_CONTROLLER_QUEUE")
        self.server = self.genTesterServer("192.168.123.1","fe:54:00:05:4d:7d")
        self.runClassifierController()
        addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.sfci)
        self.sendCmd(SERVER_CLASSIFIER_CONTROLLER_QUEUE,
            MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        yield
        # teardown
        self.sP.killPythonScript("classifierControllerCommandAgent.py")

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_delSFCI(self, setup_addSFCI):
        # exercise
        self.delSFCICmd = self.mediator.genCMDDelSFCI(self.sfc, self.sfci)
        self.sendCmd(SERVER_CLASSIFIER_CONTROLLER_QUEUE,
            MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, self.delSFCICmd)
        # verify
        self.verifyCmdRply()

    def verifyCmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL