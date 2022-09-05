#!/usr/bin/python
# -*- coding: UTF-8 -*-

import time
import uuid
import pytest

from sam.base.compatibility import screenInput
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.measurement.dcnInfoBaseMaintainer import DCNInfoBaseMaintainer
from sam.orchestration.oDcnInfoRetriever import ODCNInfoRetriever
from sam.base.request import Request, REQUEST_TYPE_GET_DCN_INFO
from sam.base.shellProcessor import ShellProcessor
from sam.test.fixtures.serverManagerStub import ServerManagerStub
from sam.test.fixtures.turbonetStub import TurbonetStub
from sam.test.fixtures.vnfControllerStub import VNFControllerStub
from sam.test.fixtures.p4ControllerStub import P4ControllerStub
from sam.test.fixtures.sffControllerStub import SFFControllerStub
from sam.test.fixtures.simulatorStub import SimulatorStub
from sam.test.testBase import TestBase


class TestMeasurerClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_collectDCNInfo(self):
        # setup
        logConfigur = LoggerConfigurator(__name__, './log',
            'testMeasurerClass.log', level='info')
        self.logger = logConfigur.getLogger()

        self.sP = ShellProcessor()

        self.sffS = SFFControllerStub()
        self.p4S = P4ControllerStub()
        self.vS = VNFControllerStub()
        self.seS = ServerManagerStub()
        self.turbonet = TurbonetStub()
        self.cleanLog()
        self.initZone()
        # self.runMeasurer()
        self.logger.info("Please start measurer. " \
            "and then press any key to continue.")
        screenInput("Type here: ")

        yield
        # teardown
        self.logger.info("Teardown")
        self.killAllModule()

    # @pytest.mark.skip(reason='Temporarly')
    def test_replyHandler(self, setup_collectDCNInfo):
        self.logger.info("test_requestHanler")
        # exercise
        self.sffS.recvCmdFromMeasurer()
        self.p4S.recvCmdFromMeasurer()
        self.vS.recvCmdFromMeasurer()
        self.seS.recvCmdFromMeasurer()
        self.turbonet.recvCmdFromMeasurer()
        time.sleep(5)
        logConfigur = LoggerConfigurator(__name__, './log',
            'measurer.log', level='debug')
        self.logger = logConfigur.getLogger()
        dib = DCNInfoBaseMaintainer()
        oDCNIR = ODCNInfoRetriever(dib, self.logger)
        oDCNIR.getDCNInfo()

        self.logger.info(dib)
        self.logger.info("Please check dib output, " \
            "and then press any key to continue.")
        screenInput("Type here: ")
        assert 1 == 1
