#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
import time
import logging

from sam.base.path import *
from sam.base.request import *
from sam.test.testBase import *
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer

logging.basicConfig(level=logging.INFO)


class TestOrchestratorClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_startOrchestrator(self):
        # setup
        logConfigur = LoggerConfigurator(__name__, './log',
            'TestOrchestratorClass.log', level='debug')
        self.logger = logConfigur.getLogger()

        self.sP = ShellProcessor()
        self.clearQueue()
        self.cleanLog()
        self.sP.runShellCommand("rm -rf ./log")
        self.killAllModule()
        self.oib = OrchInfoBaseMaintainer("localhost", "dbAgent", "123")
        self.oib.dbA.dropTable("Request")
        self.oib.dbA.dropTable("SFC")
        self.oib.dbA.dropTable("SFCI")

        self.runServerManager()
        self.runMediator()
        self.runMeasurer()
        self.runClassifierController()
        self.runSFFController()
        self.runVNFController()
        self.runOrchestrator()

        self.classifier = self.genClassifier("2.2.0.36")
        self.sfc = self.genUniDirectionSFC(self.classifier)
        self.sfci = SFCI(self._genSFCIID(), [],
            forwardingPathSet=ForwardingPathSet({}, MAPPING_TYPE_UFRR, {}))
        zoneName = self.sfc.attributes['zone']
        self.logger.debug("zoneName: {0}".format(zoneName))

        yield
        # teardown
        self.killAllModule()

    # @pytest.mark.skip(reason='Temporarly')
    def test_AddDel(self, setup_startOrchestrator):
        # exercise
        self.logger.info("press any key to send add sfc requests.")
        raw_input()
        self.logger.info("send requests")

        self.addSFCRequest = self.genAddSFCRequest(self.sfc)
        self.sendRequest(ORCHESTRATOR_QUEUE, self.addSFCRequest)

        # exercise
        self.logger.info("press any key to send add sfci requests.")
        raw_input()
        self.logger.info("send requests")

        self.addSFCIRequest = self.genAddSFCIRequest(self.sfc, self.sfci)
        self.sendRequest(ORCHESTRATOR_QUEUE, self.addSFCIRequest)

        # exercise
        self.logger.info("press any key to send del sfci requests.")
        raw_input()
        self.logger.info("send requests")

        self.delSFCIRequest = self.genDelSFCIRequest(self.sfc, self.sfci)
        self.sendRequest(ORCHESTRATOR_QUEUE, self.delSFCIRequest)

        # exercise
        self.logger.info("press any key to send del sfc requests.")
        raw_input()
        self.logger.info("send requests")

        self.delSFCRequest = self.genDelSFCRequest(self.sfc)
        self.sendRequest(ORCHESTRATOR_QUEUE, self.delSFCRequest)

        self.logger.info("press any key to quit.")
        raw_input()
