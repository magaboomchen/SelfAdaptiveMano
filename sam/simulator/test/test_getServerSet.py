#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is the component test for simulator (test _getServerSetHandler)
The work flow:
    * Mediator sends ‘GET_SERVER_SET command’ to simulator;
    * Simulator processes the command and then send back a command reply to the mediator;
    PS1:The ‘GET_SERVER_SET command’ and the corresponding ‘GET_SERVER_SET command reply’ have same cmdID;
    PS2: Class TestBase and TestSimulatorBase has many useful function;

Usage of this unit test:
    python -m pytest ./sam/simulator/test/test_getServerSet.py -s --disable-warnings
'''

import time
import logging
from time import sleep

import pytest

from sam.base.command import CMD_STATE_SUCCESSFUL
from sam.base.messageAgent import MSG_TYPE_SIMULATOR_CMD, SIMULATOR_ZONE
from sam.base.messageAgentAuxillary.msgAgentRPCConf import TEST_PORT, SIMULATOR_PORT
from sam.base.shellProcessor import ShellProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.test.fixtures.measurementStub import MeasurementStub
from sam.simulator.test.testSimulatorBase import TestSimulatorBase
from sam.simulator import simulator

MANUAL_TEST = True


class TestGetServerSetClass(TestSimulatorBase):
    def common_setup(self):
        logConfigur = LoggerConfigurator(__name__, './log',
                                        'testGetServerSetClass.log',
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
    def setup_getServerSet(self):
        self.common_setup()

        self.sP.runPythonScript(simulator.__file__)
        sleep(1)
        yield
        self.sP.killPythonScript(simulator.__file__)
        # teardown
        pass

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_getServerSet(self, setup_getServerSet):
        # exercise
        self.startMsgAgentRPCReciever("localhost", TEST_PORT)
        self.getServerSetCmd = self.measurer.genCMDGetServerSet()
        sleep(5)
        t1 = time.time()
        self.sendCmdByRPC("localhost", SIMULATOR_PORT,
                        MSG_TYPE_SIMULATOR_CMD,
                        self.getServerSetCmd)

        # verify
        self.verifyCmdRply()
        t2 = time.time()
        self.logger.info("Get server set time is {0}".format(t2-t1))

    def verifyCmdRply(self):
        cmdRply = self.recvCmdRplyByRPC("localhost", TEST_PORT)
        assert cmdRply.cmdID == self.getServerSetCmd.cmdID
        assert "servers" in cmdRply.attributes
        assert type(cmdRply.attributes["servers"]) == dict
        assert len(cmdRply.attributes["servers"]) > 0
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        assert cmdRply.attributes['zone'] == SIMULATOR_ZONE
        # self.logger.info("{0}".format(cmdRply.attributes.keys()))
        # self.logger.info("{0}".format(cmdRply.attributes["servers"]))
