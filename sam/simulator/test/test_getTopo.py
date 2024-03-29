#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is the component test for simulator (test _getTopologyHandler)
The work flow:
    * Mediator sends 'GET_TOPOLOGY command' to simulator;
    * Simulator processes the command and then send back a command reply to the mediator;
    PS1:The 'GET_TOPOLOGY command' and the corresponding 'GET_TOPOLOGY command reply' have same cmdID;
    PS2: Class TestBase and TestSimulatorBase has many useful function;
    PS3: GET_TOPOLOGY command replay's attributes includes switches and links which is the topology in effact.

Usage of this unit test:
    python -m pytest ./sam/simulator/test/test_getTopo.py -s --disable-warnings
'''

import time
from time import sleep

import pytest

from sam.base.command import CMD_STATE_SUCCESSFUL
from sam.base.messageAgent import MSG_TYPE_SIMULATOR_CMD, SIMULATOR_ZONE
from sam.base.shellProcessor import ShellProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.messageAgentAuxillary.msgAgentRPCConf import TEST_PORT, SIMULATOR_PORT
from sam.test.fixtures.measurementStub import MeasurementStub
from sam.simulator.test.testSimulatorBase import TestSimulatorBase
from sam.simulator import simulator


class TestGetTopologyClass(TestSimulatorBase):
    def common_setup(self):
        logConfigur = LoggerConfigurator(__name__, './log',
                                        'testGetTopologyClass.log',
                                        level='debug')
        self.logger = logConfigur.getLogger()

        # setup
        self.sP = ShellProcessor()
        self.cleanLog()
        self.clearQueue()
        self.killAllModule()
        self.measurer = MeasurementStub()

    @pytest.fixture(scope="function")
    def setup_getTopology(self):
        self.common_setup()

        self.sP.runPythonScript(simulator.__file__)
        sleep(1)
        yield
        self.sP.killPythonScript(simulator.__file__)
        # teardown
        pass

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_getTopology(self, setup_getTopology):
        # exercise
        self.startMsgAgentRPCReciever("localhost", TEST_PORT)
        self.getTopoCmd = self.measurer.genCMDGetTopology()
        sleep(5)
        t1 = time.time()
        self.sendCmdByRPC("localhost", SIMULATOR_PORT,
                        MSG_TYPE_SIMULATOR_CMD,
                        self.getTopoCmd)

        # verify
        self.verifyCmdRply()
        t2 = time.time()
        self.logger.info("Get topology time is {0}".format(t2-t1))

    def verifyCmdRply(self):
        cmdRply = self.recvCmdRplyByRPC("localhost", TEST_PORT)
        assert cmdRply.cmdID == self.getTopoCmd.cmdID
        assert "switches" in cmdRply.attributes
        assert "links" in cmdRply.attributes
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        assert cmdRply.attributes['zone'] == SIMULATOR_ZONE
        # self.logger.info("{0}".format(cmdRply.attributes.keys()))
        # self.logger.info("{0}".format(cmdRply.attributes["switches"]))
        # self.logger.info("{0}".format(cmdRply.attributes["links"]))
        # self.logger.info("{0}".format(cmdRply.attributes["source"]))
