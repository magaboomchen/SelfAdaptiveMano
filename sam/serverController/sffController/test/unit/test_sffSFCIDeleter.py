#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging

import pytest

from sam.base.command import CMD_STATE_SUCCESSFUL
from sam.base.shellProcessor import ShellProcessor
from sam.base.messageAgent import SFF_CONTROLLER_QUEUE, MEDIATOR_QUEUE, \
    MSG_TYPE_SFF_CONTROLLER_CMD
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.test.fixtures.vnfControllerStub import VNFControllerStub
from sam.test.testBase import TestBase, CLASSIFIER_DATAPATH_IP, SFF1_DATAPATH_IP, \
    SFF1_DATAPATH_MAC, SFCI1_0_EGRESS_IP, WEBSITE_REAL_IP, SFCI1_1_EGRESS_IP
from sam.serverController.sffController import sffControllerCommandAgent

MANUAL_TEST = True

TESTER_SERVER_DATAPATH_IP = "192.168.124.1"
TESTER_SERVER_DATAPATH_MAC = "fe:54:00:42:26:44"

logging.basicConfig(level=logging.INFO)


class TestSFFSFCIDeleterClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_delSFCI(self):
        # setup
        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genBiDirectionSFC(classifier)
        self.sfci = self.genBiDirection10BackupSFCI()
        self.mediator = MediatorStub()
        self.sP = ShellProcessor()
        self.clearQueue()
        self.server = self.genTesterServer(TESTER_SERVER_DATAPATH_IP,
            TESTER_SERVER_DATAPATH_MAC)
        self.vC = VNFControllerStub()
        self.runSFFController()
        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.sfci)
        self.sendCmd(SFF_CONTROLLER_QUEUE,
            MSG_TYPE_SFF_CONTROLLER_CMD, self.addSFCICmd)
        yield
        # teardown
        self.killSFFController()

    def runSFFController(self):
        filePath = sffControllerCommandAgent.__file__
        self.sP.runPythonScript(filePath)

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_delSFCI(self, setup_delSFCI):
        # exercise
        self.verifyAddSFCICmdRply()
        self.delSFCICmd = self.mediator.genCMDDelSFCI(self.sfc, self.sfci)
        self.sendCmd(SFF_CONTROLLER_QUEUE,
            MSG_TYPE_SFF_CONTROLLER_CMD, self.delSFCICmd)

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