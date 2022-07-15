#!/usr/bin/python
# -*- coding: UTF-8 -*-

import time
import uuid
import pytest
import logging
from sam.base.compatibility import screenInput
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.measurement.dcnInfoBaseMaintainer import DCNInfoBaseMaintainer
from sam.orchestration.oDcnInfoRetriever import ODCNInfoRetriever

from sam.base.request import Request, REQUEST_TYPE_GET_DCN_INFO
from sam.base.shellProcessor import ShellProcessor
from sam.test.fixtures.serverManagerStub import ServerManagerStub
from sam.test.fixtures.vnfControllerStub import VNFControllerStub
from sam.test.fixtures.p4ControllerStub import P4ControllerStub
from sam.test.fixtures.sffControllerStub import SFFControllerStub
from sam.test.fixtures.simulatorStub import SimulatorStub
from sam.test.testBase import TestBase

logging.basicConfig(level=logging.INFO)


class TestMeasurerClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_collectDCNInfo(self):
        # setup
        self.sP = ShellProcessor()

        self.sS = SimulatorStub()
        self.sffS = SFFControllerStub()
        self.p4S = P4ControllerStub()
        self.vS = VNFControllerStub()
        self.seS = ServerManagerStub()
        self.cleanLog()
        self.initZone()
        self.runMeasurer()
        # logging.info("Please start measurer. " \
        #     "and then press any key to continue.")
        # screenInput("Type here: ")

        yield
        # teardown
        logging.info("Teardown")
        self.killAllModule()

    @pytest.mark.skip(reason='Temporarly')
    def test_collectTopology(self, setup_collectDCNInfo):
        # exercise
        self.sS.recvCmdFromMeasurer()
        # verify
        logging.info("Please check measurer's log, " \
            "and then press any key to continue.")
        screenInput("Type here: ")
        assert 1 == 1

    # @pytest.mark.skip(reason='Temporarly')
    def test_requestHandler(self, setup_collectDCNInfo):
        logging.info("test_requestHanler")
        # exercise
        self.sS.recvCmdFromMeasurer()
        self.sffS.recvCmdFromMeasurer()
        self.p4S.recvCmdFromMeasurer()
        self.vS.recvCmdFromMeasurer()
        self.seS.recvCmdFromMeasurer()
        time.sleep(5)
        logConfigur = LoggerConfigurator(__name__, './log',
            'measurer.log', level='debug')
        self.logger = logConfigur.getLogger()
        dib = DCNInfoBaseMaintainer()
        oDCNIR = ODCNInfoRetriever(dib, self.logger)
        oDCNIR.getDCNInfo()

        logging.info(dib)
        logging.info("Please check dib output, " \
            "and then press any key to continue.")
        screenInput("Type here: ")
        assert 1 == 1

    def genGetDCNInfoRequest(self):
        request = Request(0, uuid.uuid1(), REQUEST_TYPE_GET_DCN_INFO)
        return request
