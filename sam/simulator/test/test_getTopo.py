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
from sam.base.messageAgentAuxillary.msgAgentRPCConf import *
from sam.test.fixtures.mediatorStub import *
from sam.simulator.test.testSimulatorBase import *
from sam.simulator import simulator
from time import sleep

MANUAL_TEST = True


class TestGetTopologyClass(TestSimulatorBase):
    def common_setup(self):
        logConfigur = LoggerConfigurator(__name__, './log',
                                        'testGetTopologyClass.log',
                                        level='debug')
        self.logger = logConfigur.getLogger()
        self.logger.setLevel(logging.DEBUG)

        # setup
        # self.resetRabbitMQConf(
        #     base.__file__[:base.__file__.rfind("/")] + "/rabbitMQConf.conf",
        #     "192.168.8.19", "mq", "123456")
        self.sP = ShellProcessor()
        self.cleanLog()
        self.clearQueue()
        self.killAllModule()
        self.mediator = MediatorStub()

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
        self.getTopoCmd = self.mediator.genCMDGetTopology()
        sleep(50)
        t1 = time.time()
        # self.sendCmd(SIMULATOR_QUEUE,
        #                 MSG_TYPE_SIMULATOR_CMD,
        #                 self.getTopoCmd)
        self.sendCmdByRPC("localhost", SIMULATOR_PORT,
                        MSG_TYPE_SIMULATOR_CMD,
                        self.getTopoCmd)

        # verify
        self.verifyCmdRply()
        t2 = time.time()
        self.logger.info("Get topology time is {0}".format(t2-t1))

    def verifyCmdRply(self):
        # cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        cmdRply = self.recvCmdRplyByRPC("localhost", TEST_PORT)
        assert cmdRply.cmdID == self.getTopoCmd.cmdID
        assert cmdRply.attributes.has_key("switches")
        assert cmdRply.attributes.has_key("links")
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        # self.logger.info("{0}".format(cmdRply.attributes.keys()))
        # self.logger.info("{0}".format(cmdRply.attributes["switches"]))
        # self.logger.info("{0}".format(cmdRply.attributes["links"]))
        # self.logger.info("{0}".format(cmdRply.attributes["source"]))
