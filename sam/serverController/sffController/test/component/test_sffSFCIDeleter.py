#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging

import pytest

from sam.base.command import CMD_STATE_SUCCESSFUL
from sam.base.compatibility import screenInput
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.shellProcessor import ShellProcessor
from sam.base.messageAgent import SFF_CONTROLLER_QUEUE, MEDIATOR_QUEUE, \
    MSG_TYPE_SFF_CONTROLLER_CMD, TURBONET_ZONE, MessageAgent
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.test.fixtures.vnfControllerStub import VNFControllerStub
from sam.test.testBase import TestBase, CLASSIFIER_DATAPATH_IP, SFF1_DATAPATH_IP, \
    SFF1_DATAPATH_MAC, SFCI1_0_EGRESS_IP, WEBSITE_REAL_IP, SFCI1_1_EGRESS_IP
from sam.serverController.sffController import sffControllerCommandAgent
from sam.serverController.sffController.test.component.testConfig import TESTER_SERVER_DATAPATH_IP, \
    TESTER_SERVER_DATAPATH_MAC, TESTER_DATAPATH_INTF, PRIVATE_KEY_FILE_PATH, BESS_SERVER_USER, \
    BESS_SERVER_USER_PASSWORD

MANUAL_TEST = True

logging.basicConfig(level=logging.INFO)


class TestSFFSFCIDeleterClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_delSFCI(self):
        # setup
        logConfigur = LoggerConfigurator(__name__, './log',
            'tester.log', level='debug')
        self.logger = logConfigur.getLogger()
        self._messageAgent = MessageAgent(self.logger)
        self.clearQueue()
        self.killAllModule()

        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genBiDirectionSFC(classifier)
        self.sfci = self.genBiDirection10BackupSFCI()
        self.mediator = MediatorStub()
        self.sP = ShellProcessor()

        self.server = self.genTesterServer(TESTER_SERVER_DATAPATH_IP,
                                            TESTER_SERVER_DATAPATH_MAC)
        self.vC = VNFControllerStub()

        self.runSFFController()
        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.sfci)
        self.queueName = self._messageAgent.genQueueName(SFF_CONTROLLER_QUEUE, TURBONET_ZONE)
        self.sendCmd(self.queueName,
                        MSG_TYPE_SFF_CONTROLLER_CMD,
                        self.addSFCICmd)
        self.verifyAddSFCICmdRply()

        yield

        # teardown
        self.killSFFController()

    def runSFFController(self):
        filePath = sffControllerCommandAgent.__file__
        self.sP.runPythonScript(filePath)

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_delSFCI(self, setup_delSFCI):
        # exercise
        logging.info("Press Any key to test data path!")
        screenInput()
        self.delSFCICmd = self.mediator.genCMDDelSFCI(self.sfc, self.sfci)
        self.sendCmd(self.queueName,
                        MSG_TYPE_SFF_CONTROLLER_CMD,
                        self.delSFCICmd)

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