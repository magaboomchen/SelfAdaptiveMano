#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is the component test for simulator (test _getFlowSetHandler)
The work flow:
    * Mediator sends ‘GET_FLOW_SET command’ to simulator;
    * Simulator processes the command and then send back a command reply to the mediator;
    PS1:The ‘GET_FLOW_SET command’ and the corresponding ‘GET_FLOW_SET command reply’ have same cmdID;
    PS2: Class TestBase and TestSimulatorBase has many useful function;

Usage of this unit test:
    python -m pytest ./sam/simulator/test/test_getFlowSet.py -s --disable-warnings
'''

import logging
from time import sleep

import pytest

from sam.base.command import CMD_STATE_SUCCESSFUL
from sam.base.messageAgent import SIMULATOR_QUEUE, MSG_TYPE_SIMULATOR_CMD, \
    MEDIATOR_QUEUE, SIMULATOR_ZONE
from sam.base.messageAgentAuxillary.msgAgentRPCConf import MEASURER_IP, MEASURER_PORT, SIMULATOR_IP, SIMULATOR_PORT, TEST_PORT
from sam.base.shellProcessor import ShellProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.test.fixtures.measurementStub import MeasurementStub
from sam.simulator.test.testSimulatorBase import TestSimulatorBase
from sam.simulator import simulator

MANUAL_TEST = True


class TestGetFlowSetClass(TestSimulatorBase):
    def common_setup(self):
        logConfigur = LoggerConfigurator(__name__, './log',
                                        'testGetFlowSetClass.log',
                                        level='debug')
        self.logger = logConfigur.getLogger()
        self.logger.setLevel(logging.DEBUG)

        # setup
        self.sP = ShellProcessor()
        self.cleanLog()
        self.clearQueue()
        self.killAllModule()
        self.measurer = MeasurementStub()

    @pytest.fixture(scope="function")
    def setup_getFlowSet(self):
        self.common_setup()

        self.sP.runPythonScript(simulator.__file__)
        sleep(1)
        yield
        self.sP.killPythonScript(simulator.__file__)
        # teardown
        pass

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_getFlowSet(self, setup_getFlowSet):
        # exercise
        self.getFlowSetCmd = self.measurer.genCMDGetFlowSet()
        self.startMsgAgentRPCReciever("localhost", TEST_PORT)
        self.sendCmdByRPC(SIMULATOR_IP, SIMULATOR_PORT, 
                            MSG_TYPE_SIMULATOR_CMD,
                            self.getFlowSetCmd)

        # verify
        self.verifyCmdRply()

    def verifyCmdRply(self):
        cmdRply = self.recvCmdRplyByRPC("localhost", TEST_PORT)
        # self.logger.info("{0}".format(cmdRply.attributes.keys()))
        # self.logger.info("{0}".format(cmdRply.attributes["flows"]))
        assert cmdRply.cmdID == self.getFlowSetCmd.cmdID
        assert "flows" in cmdRply.attributes
        assert type(cmdRply.attributes["flows"]) == dict
        assert len(cmdRply.attributes["flows"]) >= 0
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        assert cmdRply.attributes['zone'] == SIMULATOR_ZONE
