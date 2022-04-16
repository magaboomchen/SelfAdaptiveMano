#!/usr/bin/python
# -*- coding: UTF-8 -*-

import time
import uuid
import pytest
import logging
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.measurement.dcnInfoBaseMaintainer import DCNInfoBaseMaintainer
from sam.orchestration.oDcnInfoRetriever import ODCNInfoRetriever

from sam.base.request import Request, REQUEST_TYPE_GET_DCN_INFO
from sam.base.shellProcessor import ShellProcessor
from sam.measurement import measurer
from sam.test.fixtures.simulatorStub import SimulatorStub
from sam.test.testBase import TestBase

logging.basicConfig(level=logging.INFO)


class TestMeasurerClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_collectDCNInfo(self):
        # setup
        self.sP = ShellProcessor()

        self.sS = SimulatorStub()
        self.runMeasurer()

        yield
        # teardown
        self.killMeasurer()

    @pytest.mark.skip(reason='Temporarly')
    def test_collectTopology(self, setup_collectDCNInfo):
        # exercise
        self.sS.recvCmdFromMeasurer()
        # verify
        logging.info("Please check measurer's log, " \
            "and then press any key to continue.")
        raw_input() # type: ignore
        assert 1 == 1

    def runMeasurer(self):
        filePath = measurer.__file__
        logging.info(filePath)
        self.sP.runPythonScript(filePath)

    def killMeasurer(self):
        self.sP.killPythonScript("/measurement/measurer.py")

    # @pytest.mark.skip(reason='Temporarly')
    def test_requestHandler(self, setup_collectDCNInfo):
        logging.info("test_requestHanler")
        # exercise
        self.sS.recvCmdFromMeasurer()
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
        raw_input() # type: ignore
        assert 1 == 1


    def genGetDCNInfoRequest(self):
        request = Request(0, uuid.uuid1(), REQUEST_TYPE_GET_DCN_INFO)
        return request
