#!/usr/bin/python
# -*- coding: UTF-8 -*-

import time
import uuid
import pytest
import logging
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.messageAgentAuxillary.msgAgentRPCConf import MEASURER_IP, MEASURER_PORT
from sam.measurement.dcnInfoBaseMaintainer import DCNInfoBaseMaintainer
from sam.orchestration.oDcnInfoRetriever import ODCNInfoRetriever

from sam.simulator import simulator
from sam.base.switch import Switch, SWITCH_TYPE_NPOP
from sam.base.server import Server, SERVER_TYPE_NORMAL
from sam.base.request import Request, REQUEST_STATE_SUCCESSFUL, \
    REQUEST_TYPE_GET_DCN_INFO
from sam.base.link import Link
from sam.base.messageAgent import MEDIATOR_QUEUE, MEASURER_QUEUE, \
    MSG_TYPE_MEDIATOR_CMD_REPLY, ORCHESTRATOR_QUEUE, DCN_INFO_RECIEVER_QUEUE
from sam.base.command import CommandReply, CMD_TYPE_GET_TOPOLOGY, CMD_STATE_SUCCESSFUL
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
        self.clearQueue()

        self.runMeasurer()
        # self.runSimulator()

        yield
        # teardown
        self.killMeasurer()

    @pytest.mark.skip(reason='Temporarly')
    def test_collectTopology(self, setup_collectDCNInfo):
        # exercise
        self.sS = SimulatorStub()
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

    # def runSimulator(self):
    #     filePath = simulator.__file__
    #     logging.info(filePath)
    #     self.sP.runPythonScript(filePath)

    # def killMeasurer(self):
    #     self.sP.killPythonScript("/simulator/simulator.py")

    # @pytest.mark.skip(reason='Temporarly')
    def test_requestHandler(self, setup_collectDCNInfo):
        logging.info("test_requestHanler")
        # exercise
        self.sS = SimulatorStub()
        self.sS.recvCmdFromMeasurer()
        time.sleep(5)
        logConfigur = LoggerConfigurator(__name__, './log',
            'measurer.log', level='debug')
        self.logger = logConfigur.getLogger()
        dib = DCNInfoBaseMaintainer()
        oDCNIR = ODCNInfoRetriever(dib, self.logger)
        oDCNIR.getDCNInfo()
        # request = self.genGetDCNInfoRequest()
        # tmpMA = self.sendRequestByGRPC(MEASURER_IP, MEASURER_PORT, request)

        # verify
        # reply = self.recvReplyByRPC(tmpMA.listenIP, tmpMA.listenPort)
        # assert reply.requestID == request.requestID
        # assert reply.requestState == REQUEST_STATE_SUCCESSFUL

        # for key,values in reply.attributes.items():
        #     logging.info("{0},{1}".format(key, values))
            # if type(values) == list:
            #     for item in values:
            #         logging.info(item)
        
        # del tmpMA

        logging.info(dib)
        logging.info("Please check dib output, " \
            "and then press any key to continue.")
        raw_input() # type: ignore
        assert 1 == 1


    def genGetDCNInfoRequest(self):
        request = Request(0, uuid.uuid1(), REQUEST_TYPE_GET_DCN_INFO)
        return request
