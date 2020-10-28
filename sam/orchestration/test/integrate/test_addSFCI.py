#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
import time
import logging

from sam.test.testBase import *
from sam.base.request import *
from sam.orchestration import orchestrator
from sam.mediator import mediator
from sam.measurement import measurer
from sam.serverController.classifierController import classifierControllerCommandAgent
from sam.serverController.sffController import sffControllerCommandAgent
from sam.serverController.vnfController import vnfController
from sam.serverController.serverManager import serverManager

logging.basicConfig(level=logging.INFO)


class TestOrchestratorADDSFCIClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_startOrchestrator(self):
        # setup
        self.sP = ShellProcessor()
        self.clearQueue()
        self.cleanLog()
        self.killAllModule()

        # self.runOrchestrator()
        self.runServerManager()
        self.runMediator()
        self.runMeasurer()
        self.runSFFController()
        self.runClassifierController()
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

    def runOrchestrator(self):
        filePath = orchestrator.__file__
        self.sP.runPythonScript(filePath)

    def runMeasurer(self):
        filePath = measurer.__file__
        self.sP.runPythonScript(filePath)

    def runMediator(self):
        filePath = mediator.__file__
        self.sP.runPythonScript(filePath)

    def runSFFController(self):
        filePath = sffControllerCommandAgent.__file__
        self.sP.runPythonScript(filePath)

    def runClassifierController(self):
        filePath = classifierControllerCommandAgent.__file__
        self.sP.runPythonScript(filePath)

    def runVNFController(self):
        filePath = vnfController.__file__
        self.sP.runPythonScript(filePath)

    def runServerManager(self):
        filePath = serverManager.__file__
        self.sP.runPythonScript(filePath)

    def killAllModule(self):
        self.sP.runShellCommand("python ../../../toolkit/killAllSAMPythonScripts.py")
