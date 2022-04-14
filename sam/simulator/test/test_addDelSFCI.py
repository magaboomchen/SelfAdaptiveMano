#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is an example for writing unit test for simulator (test _addSFCIHandler)
The work flow:
    * Mediator sends ‘ADD_SFCI command’ to simulator;
    * Simulator processes the command and then send back a command reply to the mediator;
    PS1:The ‘ADD_SFCI command’ and the corresponding ‘ADD_SFCI command reply’ have same cmdID;
    PS2: Class TestBase and TestSimulatorBase has many useful function;

Usage of this unit test:
    sudo python -m pytest ./test_addDelSFCI.py -s --disable-warnings
'''

from time import sleep

import pytest

from sam import base
from sam.base.sfc import *
from sam.base.vnf import *
from sam.base.server import *
from sam.base.command import *
from sam.base.socketConverter import SocketConverter, BCAST_MAC
from sam.base.shellProcessor import ShellProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.simulator.test.testSimulatorBase import *
from sam.simulator import simulator

MANUAL_TEST = True


class TestAddSFCIClass(TestSimulatorBase):
    def common_setup(self):
        logConfigur = LoggerConfigurator(__name__, './log',
                                            'testAddSFCIClass.log',
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
    def setup_addOneSFCIWithVNFIOnAServer(self):
        self.common_setup()

        # you can overwrite following function to test different sfc/sfci
        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genUniDirectionSFC(classifier)
        self.sfci = self.genUniDirection10BackupSFCI()

        self.sP.runPythonScript(simulator.__file__)
        sleep(1)
        yield
        self.sP.killPythonScript(simulator.__file__)
        # teardown
        self.clearQueue()
        self.killAllModule()

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_addOneSFCIWithVNFIOnAServer(self, setup_addOneSFCIWithVNFIOnAServer):
        # exercise
        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.sfci)
        self.sendCmd(SIMULATOR_QUEUE, MSG_TYPE_SIMULATOR_CMD , self.addSFCICmd)

        # verify
        self.verifyAddSFCICmdRply()

    def verifyAddSFCICmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    @pytest.fixture(scope="function")
    def setup_addThenDelOneSFCIWithVNFIOnAServer(self):
        self.common_setup()

        # you can overwrite following function to test different sfc/sfci
        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genUniDirectionSFC(classifier)
        self.sfci = self.genUniDirection10BackupSFCI()
        self.sP.runPythonScript(simulator.__file__)
        sleep(1)

        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.sfci)
        self.sendCmd(SIMULATOR_QUEUE, MSG_TYPE_SIMULATOR_CMD , self.addSFCICmd)
        self.verifyAddSFCICmdRply()

        yield
        self.sP.killPythonScript(simulator.__file__)
        # teardown
        self.clearQueue()
        self.killAllModule()

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_addThenDelOneSFCIWithVNFIOnAServer(self, setup_addThenDelOneSFCIWithVNFIOnAServer):
        # exercise
        self.delSFCICmd = self.mediator.genCMDDelSFCI(self.sfc, self.sfci)
        self.sendCmd(SIMULATOR_QUEUE, MSG_TYPE_SIMULATOR_CMD , self.delSFCICmd)

        # verify
        self.verifyDelSFCICmdRply()

    def verifyDelSFCICmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

