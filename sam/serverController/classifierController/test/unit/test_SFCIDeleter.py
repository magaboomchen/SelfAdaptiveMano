#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging

import pytest

from sam.base.command import CMD_STATE_SUCCESSFUL
from sam.base.shellProcessor import ShellProcessor
from sam.base.messageAgent import SERVER_CLASSIFIER_CONTROLLER_QUEUE, \
    MEDIATOR_QUEUE, MSG_TYPE_CLASSIFIER_CONTROLLER_CMD
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.test.testBase import TestBase, CLASSIFIER_DATAPATH_IP

MANUAL_TEST = True

TESTER_SERVER_DATAPATH_IP = "192.168.123.1"
TESTER_SERVER_DATAPATH_MAC = "fe:54:00:05:4d:7d"

logging.basicConfig(level=logging.INFO)


class TestSFCIDeleterClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_addSFCI(self):
        # setup
        logConfigur = LoggerConfigurator(__name__, './log',
            'TestOrchestratorClass.log', level='debug')
        self.logger = logConfigur.getLogger()

        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genBiDirectionSFC(classifier)
        self.sfci = self.genBiDirection10BackupSFCI()
        self.mediator = MediatorStub()
        self.sP = ShellProcessor()
        self.clearQueue()
        self.server = self.genTesterServer("192.168.123.1","fe:54:00:05:4d:7d")
        self.runClassifierController()
        addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.sfci)
        self.sendCmd(SERVER_CLASSIFIER_CONTROLLER_QUEUE,
            MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        yield
        # teardown
        self.killClassifierController()

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_delSFCAndSFCI(self, setup_addSFCI):
        # exercise
        self.delSFCICmd = self.mediator.genCMDDelSFCI(self.sfc, self.sfci)
        self.sendCmd(SERVER_CLASSIFIER_CONTROLLER_QUEUE,
            MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, self.delSFCICmd)
        # verify
        self.verifyDelSFCICmdRply()

        self.logger.info("press any key to send del sfc cmd.")
        raw_input()  # type: ignore
        self.logger.info("send cmd")

        # exercise
        self.delSFCCmd = self.mediator.genCMDDelSFC(self.sfc)
        self.sendCmd(SERVER_CLASSIFIER_CONTROLLER_QUEUE,
            MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, self.delSFCCmd)
        # verify
        self.verifyDelSFCCmdRply()

    def verifyDelSFCICmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def verifyDelSFCCmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCCmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
