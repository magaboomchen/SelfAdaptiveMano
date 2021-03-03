#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is an example for writing unit test for simulator (test _getFlowSetHandler)
The work flow:
    * Mediator sends ‘GET_FLOW_SET command’ to simulator;
    * Simulator processes the command and then send back a command reply to the mediator;
    PS1:The ‘GET_FLOW_SET command’ and the corresponding ‘GET_FLOW_SET command reply’ have same cmdID;
    PS2: Class TestBase and TestSimulatorBase has many useful function;

Usage of this unit test:
    sudo python -m pytest ./test_getFlowSet.py -s --disable-warnings
'''

import time

import pytest

from sam import base
from sam.base.sfc import *
from sam.base.vnf import *
from sam.base.server import *
from sam.base.command import *
from sam.base.socketConverter import *
from sam.base.shellProcessor import ShellProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.test.fixtures.mediatorStub import *
from sam.simulator.test.testSimulatorBase import *

MANUAL_TEST = True


class TestGetFlowSetClass(TestSimulatorBase):
    def common_setup(self):
        logConfigur = LoggerConfigurator(__name__, './log',
                                        'testGetFlowSetClass.log',
                                        level='debug')
        self.logger = logConfigur.getLogger()
        self.logger.setLevel(logging.DEBUG)

        # setup
        self.resetRabbitMQConf(
            base.__file__[:base.__file__.rfind("/")] + "/rabbitMQConf.conf",
            "192.168.5.124", "mq", "123456")
        self.sP = ShellProcessor()
        self.cleanLog()
        self.clearQueue()
        self.killAllModule()
        self.mediator = MediatorStub()

    @pytest.fixture(scope="function")
    def setup_getFlowSet(self):
        self.common_setup()

        yield
        # teardown
        pass

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_getFlowSet(self, setup_getFlowSet):
        # exercise
        self.getFlowSetCmd = self.mediator.genCMDGetFlowSet()
        self.sendCmd(SIMULATOR_QUEUE, MSG_TYPE_SIMULATOR_CMD,
                        self.getFlowSetCmd)

        # verify
        self.verifyCmdRply()

    def verifyCmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.getFlowSetCmd.cmdID
        assert cmdRply.attributes == {}
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL