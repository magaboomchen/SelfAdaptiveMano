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
    MEDIATOR_QUEUE, SIMULATOR_ZONE
from sam.base.shellProcessor import ShellProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.vnf import VNF_TYPE_FW, VNF_TYPE_MONITOR, VNF_TYPE_RATELIMITER
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.simulator.test.testSimulatorBase import TestSimulatorBase
from sam.simulator import simulator
from sam.test.testBase import CLASSIFIER_DATAPATH_IP

MANUAL_TEST = True


class TestGetSFCIStatusClass(TestSimulatorBase):
    def common_setup(self):
        logConfigur = LoggerConfigurator(__name__, './log',
                                        'testGetSFCIStatusClass.log',
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
        self.addSFCI2Simulator()

        self.getSFCIStatusCmd = self.mediator.genCMDGetSFCIStatus()
        self.sendCmd(SIMULATOR_QUEUE, MSG_TYPE_SIMULATOR_CMD,
                        self.getSFCIStatusCmd)

        # verify
        self.verifyGetSFCIStatusCmdRply()

    def addSFCI2Simulator(self):
        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP,
                            serverBasedClassifier=self.serverBasedClassifier)
        for sfcLength in [1,2,3]:
            sfc = self.genUniDirectionSFC(classifier, sfcLength=sfcLength)
            self.sfcList.append(sfc)
            sfci = self.genUniDirection10BackupServerNFVISFCI(
                                sfcLength=sfcLength,
                    serverBasedClassifier=self.serverBasedClassifier)
            self.sfciList.append(sfci)

        for idx in [0,1,2]:
            logging.info("test idx {0}".format(idx))
            # exercise
            self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfcList[idx],
                                                        self.sfciList[idx])
            self.sendCmd(SIMULATOR_QUEUE, MSG_TYPE_SIMULATOR_CMD,
                                                    self.addSFCICmd)

            # verify
            self.verifyAddSFCICmdRply()

    def verifyAddSFCICmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        assert cmdRply.attributes['zone'] == SIMULATOR_ZONE

    def verifyGetSFCIStatusCmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.getSFCIStatusCmd.cmdID
        assert "sfcisDict" in cmdRply.attributes
        assert type(cmdRply.attributes["sfcisDict"]) == dict
        assert len(cmdRply.attributes["sfcisDict"]) >= 0
        assert cmdRply.cmdStatus == CMD_STATE_SUCCESSFUL
        assert cmdRply.attributes['zone'] == SIMULATOR_ZONE
        sfcisDict = cmdRply.attributes["sfcisDict"]
        for sfciID,sfci in sfcisDict.items():
            assert sfci.sfciID == sfciID
            
            sloRealTimeValue = sfci.sloRealTimeValue
            assert sloRealTimeValue.availability >= 99.95
            assert sloRealTimeValue.latencyBound <= 35
            assert sloRealTimeValue.latency <= 35
            assert sloRealTimeValue.throughput <= 0.1
            assert sloRealTimeValue.dropRate <= 100

            assert len(sfci.vnfiSequence) != 0
            vnfiSequence = sfci.vnfiSequence
            for vnfi in vnfiSequence:
                vnfiStatus = vnfi.vnfiStatus
                assert vnfiStatus.inputTrafficAmount > 0
                assert vnfiStatus.inputPacketAmount > 0
                assert vnfiStatus.outputTrafficAmount > 0
                assert vnfiStatus.outputPacketAmount > 0
                vnfType = vnfiStatus.vnfType
                if vnfType == VNF_TYPE_FW:
                    assert vnfiStatus.state <= 100
                elif vnfType == VNF_TYPE_MONITOR:
                    assert vnfiStatus.state <= 100
                elif vnfType == VNF_TYPE_RATELIMITER:
                    assert vnfiStatus.state <= 100
                else:
                    raise ValueError("Unknown vnf type {0}".format(vnfType))
