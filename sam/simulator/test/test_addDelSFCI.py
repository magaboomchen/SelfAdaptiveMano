#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is the component test for simulator (test _addSFCIHandler)
The work flow:
    * Mediator sends ‘ADD_SFCI command’ to simulator;
    * Simulator processes the command and then send back a command reply to the mediator;
    PS1:The ‘ADD_SFCI command’ and the corresponding ‘ADD_SFCI command reply’ have same cmdID;
    PS2: Class TestBase and TestSimulatorBase has many useful function;

Usage of this unit test:
    python -m pytest ./sam/simulator/test/test_addDelSFCI.py -s --disable-warnings
'''

import logging
from time import sleep

import pytest

from sam.base.messageAgent import SIMULATOR_QUEUE, MSG_TYPE_SIMULATOR_CMD, \
    MEDIATOR_QUEUE, SIMULATOR_ZONE
from sam.base.command import CMD_STATE_SUCCESSFUL
from sam.base.shellProcessor import ShellProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.simulator.test.testSimulatorBase import TestSimulatorBase, CLASSIFIER_DATAPATH_IP
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
        self.sP = ShellProcessor()
        self.cleanLog()
        self.clearQueue()
        self.killAllModule()
        self.mediator = MediatorStub()

        self.sfcList = []
        self.sfciList = []
        self.serverBasedClassifier = False






    @pytest.fixture(scope="function")
    def setup_addOneSFCIWithVNFIOnAServer(self):
        self.common_setup()

        # you can overwrite following function to test different sfc/sfci
        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP,
                            serverBasedClassifier=self.serverBasedClassifier)
        for sfcLength in [1,2,3]:
            sfc = self.genUniDirectionSFC(classifier, sfcLength=sfcLength)
            self.sfcList.append(sfc)
            sfci = self.genUniDirection10BackupServerNFVISFCI(
                                sfcLength=sfcLength,
                    serverBasedClassifier=self.serverBasedClassifier)
            self.sfciList.append(sfci)

        self.sP.runPythonScript(simulator.__file__)
        sleep(1)
        yield
        self.sP.killPythonScript(simulator.__file__)
        # teardown
        self.clearQueue()
        self.killAllModule()

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_addOneSFCIWithVNFIOnAServer(self,
                                        setup_addOneSFCIWithVNFIOnAServer):
        for idx in [0,1,2]:
            logging.info("test idx {0}".format(idx))
            # exercise
            self.addSFCCmd = self.mediator.genCMDAddSFC(self.sfcList[idx])
            self.sendCmd(SIMULATOR_QUEUE, MSG_TYPE_SIMULATOR_CMD,
                                                    self.addSFCCmd)

            # verify
            self.verifyAddSFCCmdRply()

            # exercise
            self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfcList[idx],
                                                        self.sfciList[idx])
            self.sendCmd(SIMULATOR_QUEUE, MSG_TYPE_SIMULATOR_CMD,
                                                    self.addSFCICmd)

            # verify
            self.verifyAddSFCICmdRply()

    def verifyAddSFCCmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCCmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        assert cmdRply.attributes['zone'] == SIMULATOR_ZONE

    def verifyAddSFCICmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        assert cmdRply.attributes['zone'] == SIMULATOR_ZONE






    @pytest.fixture(scope="function")
    def setup_addOneSFCIWithP4VNFIOnASwitch(self):
        self.common_setup()

        # you can overwrite following function to test different sfc/sfci
        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP,
                            serverBasedClassifier=self.serverBasedClassifier)
        for sfcLength in [1,2,3]:
            sfc = self.genUniDirectionSFC(classifier, sfcLength=sfcLength)
            self.sfcList.append(sfc)
            sfci = self.genUniDirection10BackupP4NFVISFCI(sfcLength=sfcLength,
                                serverBasedClassifier=self.serverBasedClassifier)
            self.sfciList.append(sfci)

        self.sP.runPythonScript(simulator.__file__)
        sleep(1)
        yield
        self.sP.killPythonScript(simulator.__file__)
        # teardown
        self.clearQueue()
        self.killAllModule()

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_addOneSFCIWithP4VNFIOnASwitch(self, 
                                        setup_addOneSFCIWithP4VNFIOnASwitch):
        for idx in [0,1,2]:
            logging.info("test idx {0}".format(idx))
            # exercise
            self.addSFCCmd = self.mediator.genCMDAddSFC(self.sfcList[idx])
            self.sendCmd(SIMULATOR_QUEUE, MSG_TYPE_SIMULATOR_CMD,
                                                    self.addSFCCmd)

            # verify
            self.verifyAddSFCCmdRply()

            # exercise
            self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfcList[idx],
                                                        self.sfciList[idx])
            self.sendCmd(SIMULATOR_QUEUE, MSG_TYPE_SIMULATOR_CMD,
                                                self.addSFCICmd)

            # verify
            self.verifyAddSFCICmdRply()






    @pytest.fixture(scope="function")
    def setup_addThenDelOneSFCIWithVNFIOnAServer(self):
        self.common_setup()

        # you can overwrite following function to test different sfc/sfci
        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP,
                                serverBasedClassifier=self.serverBasedClassifier)
        self.sfc = self.genUniDirectionSFC(classifier)
        self.sfci = self.genUniDirection10BackupServerNFVISFCI(
                    serverBasedClassifier=self.serverBasedClassifier)

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
        self.addSFCCmd = self.mediator.genCMDAddSFC(self.sfc)
        self.sendCmd(SIMULATOR_QUEUE, MSG_TYPE_SIMULATOR_CMD,
                                                self.addSFCCmd)

        # verify
        self.verifyAddSFCCmdRply()

        # exercise
        self.delSFCICmd = self.mediator.genCMDDelSFCI(self.sfc, self.sfci)
        self.sendCmd(SIMULATOR_QUEUE, MSG_TYPE_SIMULATOR_CMD , self.delSFCICmd)

        # verify
        self.verifyDelSFCICmdRply()

    def verifyDelSFCICmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        assert cmdRply.attributes['zone'] == SIMULATOR_ZONE

