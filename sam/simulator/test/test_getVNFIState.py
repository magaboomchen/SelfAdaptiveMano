#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is an example for writing unit test for simulator (test _getVNFIStateHandler)
The work flow:
    * Mediator sends ‘GET_VNFI_STATE command’ to simulator;
    * Simulator processes the command and then send back a command reply to the mediator;
    * Cautions! You just need send back all VNFI objects in a dict, e.g. {"vnfiID": VNFI()}
    PS1:The ‘GET_VNFI_STATE command’ and the corresponding ‘GET_VNFI_STATE command reply’ have same cmdID;
    PS2: Class TestBase and TestSimulatorBase has many useful function;

Usage of this unit test:
    sudo python -m pytest ./test_getVNFIState.py -s --disable-warnings
'''

import logging
from time import sleep

import pytest

from sam.base.command import CMD_STATE_SUCCESSFUL
from sam.base.messageAgent import SIMULATOR_QUEUE, MSG_TYPE_SIMULATOR_CMD, \
    MEDIATOR_QUEUE, SIMULATOR_ZONE
from sam.base.shellProcessor import ShellProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.simulator.test.testSimulatorBase import TestSimulatorBase
from sam.simulator import simulator

MANUAL_TEST = True


class TestGetVNFIStateClass(TestSimulatorBase):
    def common_setup(self):
        logConfigur = LoggerConfigurator(__name__, './log',
                                        'testGetVNFIStateClass.log',
                                        level='debug')
        self.logger = logConfigur.getLogger()
        self.logger.setLevel(logging.DEBUG)

        # setup
        # self.resetRabbitMQConf(
        #     base.__file__[:base.__file__.rfind("/")] + "/rabbitMQConf.json",
        #     "192.168.8.19", "mq", "123456")
        self.sP = ShellProcessor()
        self.cleanLog()
        self.clearQueue()
        self.killAllModule()
        self.mediator = MediatorStub()

    @pytest.fixture(scope="function")
    def setup_getVNFIState(self):
        self.common_setup()

        self.sP.runPythonScript(simulator.__file__)
        sleep(1)
        yield
        self.sP.killPythonScript(simulator.__file__)
        # teardown
        pass

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_getVNFIState(self, setup_getVNFIState):
        # exercise
        self.getVNFIStateCmd = self.mediator.genCMDGetVNFIState()
        self.sendCmd(SIMULATOR_QUEUE, MSG_TYPE_SIMULATOR_CMD,
                        self.getVNFIStateCmd)

        # verify
        self.verifyCmdRply()

    def verifyCmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.getVNFIStateCmd.cmdID
        assert "vnfiState" in cmdRply.attributes
        assert type(cmdRply.attributes["vnfiState"]) == dict
        assert len(cmdRply.attributes["vnfiState"]) >= 0
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        assert cmdRply.attributes['zone'] == SIMULATOR_ZONE
