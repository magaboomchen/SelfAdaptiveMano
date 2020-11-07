#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
import time
import logging

from sam.test.testBase import *
from sam.base.request import *

logging.basicConfig(level=logging.INFO)


class TestOrchestratorADDSFCIClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_startOrchestrator(self):
        # setup
        self.sP = ShellProcessor()
        self.clearQueue()
        self.cleanLog()
        self.sP.runShellCommand("rm -rf ./log")
        self.killAllModule()

        # self.runOrchestrator()
        self.runServerManager()
        self.runMediator()
        self.runMeasurer()
        self.runClassifierController()
        self.runSFFController()
        self.runVNFController()

        yield
        # teardown
        # self.killAllModule()

    # @pytest.mark.skip(reason='Temporarly')
    def test_REQUEST_TYPE_ADD_SFCI(self, setup_startOrchestrator):
        # exercise
        classifier = self.genClassifier("2.2.0.36")
        sfc = self.genUniDirectionSFC(classifier)
        zoneName = sfc.attributes['zone']
        self.request = self.genAddSFCIRequest(sfc)
        self.sendRequest(ORCHESTRATOR_QUEUE, self.request)

        # verify
        reply = self.recvReply(REQUEST_PROCESSOR_QUEUE)
        assert reply.requestID == self.request.requestID
        assert reply.requestState == REQUEST_STATE_SUCCESSFUL
