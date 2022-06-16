#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is an example for writing unit test for simulator (test _getSFCIStatusHandler)
The work flow:
    * Mediator sends ‘GET_SFCI_Status command’ to simulator;
    * Simulator processes the command and then send back a command reply to the mediator;
    * Cautions! You just need send back all SFCI objects in a dict, e.g. {"sfciID": SFCI()}
    * We should check whether variable in SFCI object has been updated.
    PS1:The ‘GET_SFCI_Status command’ and the corresponding ‘GET_SFCI_Status command reply’ have same cmdID;
    PS2: Class TestBase and TestSimulatorBase has many useful function;

Usage of this unit test:
    sudo python -m pytest ./test_getSFCIStatus.py -s --disable-warnings
'''

import logging
from time import sleep

import pytest

from sam.base.command import CMD_STATE_SUCCESSFUL
from sam.base.messageAgent import SIMULATOR_QUEUE, MSG_TYPE_SIMULATOR_CMD, \
    MEDIATOR_QUEUE
from sam.base.shellProcessor import ShellProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.simulator.test.testSimulatorBase import TestSimulatorBase
from sam.simulator import simulator

MANUAL_TEST = True


class TestGetSFCIStatusClass(TestSimulatorBase):
    def common_setup(self):
        logConfigur = LoggerConfigurator(__name__, './log',
                                        'testGetSFCIStatusClass.log',
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
    def setup_getSFCIStatus(self):
        self.common_setup()

        self.sP.runPythonScript(simulator.__file__)
        sleep(1)
        yield
        self.sP.killPythonScript(simulator.__file__)
        # teardown
        pass

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_getSFCIStatus(self, setup_getSFCIStatus):
        # exercise
        self.getSFCIStatusCmd = self.mediator.genCMDGetSFCIStatus()
        self.sendCmd(SIMULATOR_QUEUE, MSG_TYPE_SIMULATOR_CMD,
                        self.getSFCIStatusCmd)

        # verify
        self.verifyCmdRply()

    def verifyCmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.getSFCIStatusCmd.cmdID
        assert cmdRply.attributes.has_key("sfciStatus")
        assert type(cmdRply.attributes["sfciStatus"]) == dict
        assert len(cmdRply.attributes["sfciStatus"]) >= 0
        assert cmdRply.cmdStatus == CMD_STATE_SUCCESSFUL
