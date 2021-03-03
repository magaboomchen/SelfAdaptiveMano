#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is an example for writing unit test for simulator (test _getTopologyHandler)
The work flow:
    * Mediator sends ‘GET_TOPOLOGY command’ to simulator;
    * Simulator processes the command and then send back a command reply to the mediator;
    PS1:The ‘GET_TOPOLOGY command’ and the corresponding ‘GET_TOPOLOGY command reply’ have same cmdID;
    PS2: Class TestBase and TestSimulatorBase has many useful function;
    PS3: GET_TOPOLOGY command replay's attributes includes switches and links which is the topology in effact.

Usage of this unit test:
    sudo python -m pytest ./test_getTopo.py -s --disable-warnings
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


class TestGetTopologyClass(TestSimulatorBase):
    def common_setup(self):
        logConfigur = LoggerConfigurator(__name__, './log',
                                        'testGetTopologyClass.log',
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
    def setup_getTopology(self):
        self.common_setup()

        yield
        # teardown
        pass

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_getTopology(self, setup_getTopology):
        # exercise
        self.getTopoCmd = self.mediator.genCMDGetTopology()
        self.sendCmd(SIMULATOR_QUEUE,
                        MSG_TYPE_SIMULATOR_CMD,
                        self.getTopoCmd)

        # verify
        self.verifyCmdRply()

    def verifyCmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.getTopoCmd.cmdID
        assert cmdRply.attributes.has_key("switches")
        assert cmdRply.attributes.has_key("links")
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL