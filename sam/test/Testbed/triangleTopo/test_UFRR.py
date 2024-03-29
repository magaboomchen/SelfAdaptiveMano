#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
You need setup PICA8 switch testbed.
Wired switch and server's port as Onenote: Verify RYU
'''

import logging

import pytest

from sam import base
from sam.base.compatibility import screenInput
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.shellProcessor import ShellProcessor
from sam.base.messageAgent import MessageAgent
from sam.test.testBase import CLASSIFIER_DATAPATH_IP
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.test.Testbed.triangleTopo.testbedFRR import TestbedFRR


class TestUFRRClass(TestbedFRR):
    @pytest.fixture(scope="function")
    def setup_addUniSFCI(self):
        # setup
        logConfigur = LoggerConfigurator(__name__, './log',
                                            'testUFRRClass.log',
                                            level='debug')
        self.logger = logConfigur.getLogger()

        self.resetRabbitMQConf(
            base.__file__[:base.__file__.rfind("/")] + "/rabbitMQConf.json",
            "192.168.0.194", "mq", "123456")
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

    # @pytest.mark.skip(reason='Temporarly')
    def test_UFRRAddUniSFCI(self, setup_addUniSFCI):
        self.logger.info("You need start ryu-manager and mininet manually!"
            "Then press any key to continue!")
        screenInput() 

        self.addSFC2NetworkController()
        self.addSFCI2NetworkController()

        self.logger.info("Please input any key to test "
            "server software failure\n"
            "After the test, "
            "Press any key to quit!")
        screenInput() 
        self.sendHandleServerSoftwareFailureCmd()
        # TODO: kill serverAgent to test server failure protection

        self.logger.info("Please input mode 0 into mininet\n"
            "After the test, "
            "Press any key to quit!")
        screenInput() 
