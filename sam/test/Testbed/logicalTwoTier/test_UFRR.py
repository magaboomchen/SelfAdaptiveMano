#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
Before start test, please run ch17/ufrr/logicalTwoTier/init_bridge.sh in pica8-switch1 and pica8-switch2
'''

import sys
import time
import logging
import copy

import pytest
from ryu.controller import dpset

from sam import base
from sam.ryu.topoCollector import TopoCollector
from sam.base.path import *
from sam.base.vnf import *
from sam.base.pickleIO import *
from sam.base.shellProcessor import ShellProcessor
from sam.test.testBase import *
from sam.test.fixtures.vnfControllerStub import *
from sam.test.Testbed.logicalTwoTier.testbedFRR import *
from sam.orchestration.oSFCAdder import *
from sam.measurement.dcnInfoBaseMaintainer import *

logging.basicConfig(level=logging.INFO)
logging.getLogger("pika").setLevel(logging.WARNING)


class TestUFRRClass(TestbedFRR):
    @pytest.fixture(scope="function")
    def setup_addUniSFCI(self):
        # setup
        self.resetRabbitMQConf(
            base.__file__[:base.__file__.rfind("/")] + "/rabbitMQConf.conf",
            "192.168.0.194", "mq", "123456")
        self.sP = ShellProcessor()
        self.sP.runShellCommand("rm -rf ./log")
        self.cleanLog()
        self.clearQueue()
        self.killAllModule()

        logConfigur = LoggerConfigurator(__name__, './log',
            'testUFRRrotectionClass.log', level='info')
        self.logger = logConfigur.getLogger()

        self._messageAgent = MessageAgent()
        self.zoneName = PICA8_ZONE
        self.mediator = MediatorStub()
        self.pIO = PickleIO()

        self.loadInstance()
        self.loadSolution()
        self._dib = DCNInfoBaseMaintainer()
        self._updateDib()
        self.oSA = OSFCAdder(self._dib, self.logger)
        self.oSA.zoneName = PICA8_ZONE
        self.makeCmdList(self.mmlSFCSolution)

        self.logger.info("self.mmlSFCSolution: {0}".format(self.mmlSFCSolution))

        # self.analysePostFailureServerUtilization(self.mmlSFCSolution, 10004)

        self.oS = OrchestrationStub()
        self.oS.startRecv()

        # self.runServerManager()
        self.runClassifierController()
        self.runSFFController()
        self.runVNFController()
        self.runMediator()

        self.expectedCmdRplyDict = {}

        yield
        # teardown
        self.recoveryServerSoftwareFailure()
        self.delSFCIs()
        self.killClassifierController()
        self.killSFFController()
        self.killVNFController()
        self.killServerManager()
        self.killMediator()

    def test_addUniSFCI(self, setup_addUniSFCI):
        time.sleep(2)
        self.logger.info("You need to start ryu-manager manually!"
            "Then press any key to continue!")
        raw_input()

        # return 

        # self.addSFCCmdList = self.addSFCCmdList[:1]

        # self.logger.warning("addSFCCmdList {0}".format(self.addSFCCmdList))

        # self.logger.warning("\n\n\n")

        # self.logger.warning("addSFCICmdList {0}".format(self.addSFCICmdList[:1]))

        # return None

        self.addSFCIs()

        self.logger.info("Please input any key to test "
            "server software failure\n"
            "After the test, "
            "Press any key to quit!")
        raw_input()
        t1 = time.time()
        self.makeServerSoftwareFailure()
        self.sendHandleServerSoftwareFailureCmd()
        t2 = time.time()
        self.logger.info("t2-t1: {0}".format(t2-t1))

        self.logger.info("Press any key to quit!")
        raw_input()
