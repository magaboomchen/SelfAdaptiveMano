#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is the component test for simulator (test _getSFCIStatusHandler)
The work flow:
    * Mediator sends ‘GET_SFCI_Status command’ to simulator;
    * Simulator processes the command and then send back a command reply to the mediator;
    * Cautions! You just need send back all SFCI objects in a dict, e.g. {"sfciID": SFCI()}
    * We should check whether variable in SFCI object has been updated.
    PS1:The ‘GET_SFCI_Status command’ and the corresponding ‘GET_SFCI_Status command reply’ have same cmdID;
    PS2: Class TestBase and TestSimulatorBase has many useful function;

Usage of this unit test:
    python -m pytest ./sam/simulator/test/test_getSFCIStatus.py -s --disable-warnings
'''

import logging
from time import sleep

import pytest

from sam.base.command import CMD_STATE_SUCCESSFUL
from sam.base.messageAgent import SIMULATOR_QUEUE, MSG_TYPE_SIMULATOR_CMD, \
    MEDIATOR_QUEUE, SIMULATOR_ZONE
from sam.base.messageAgentAuxillary.msgAgentRPCConf import SIMULATOR_PORT, TEST_PORT
from sam.base.shellProcessor import ShellProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.vnf import VNF_TYPE_FW, VNF_TYPE_MONITOR, VNF_TYPE_RATELIMITER, VNFIStatus
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.test.fixtures.measurementStub import MeasurementStub
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
        self.cleanSFCAndSFCIInDB()
        self.mediator = MediatorStub()
        self.measurer = MeasurementStub()

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
        self.startMsgAgentRPCReciever("localhost", TEST_PORT)

        self.getSFCIStatusCmd = self.measurer.genCMDGetSFCIState()
        self.sendCmdByRPC("localhost", SIMULATOR_PORT,
                        MSG_TYPE_SIMULATOR_CMD,
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
                    serverBasedClassifier=self.serverBasedClassifier,
                    vnfType=VNF_TYPE_RATELIMITER)
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
        cmdRply = self.recvCmdRplyByRPC("localhost", TEST_PORT)
        assert cmdRply.cmdID == self.getSFCIStatusCmd.cmdID
        assert "sfcisDict" in cmdRply.attributes
        assert type(cmdRply.attributes["sfcisDict"]) == dict
        assert len(cmdRply.attributes["sfcisDict"]) >= 0
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        assert cmdRply.attributes['zone'] == SIMULATOR_ZONE
        sfcisDict = cmdRply.attributes["sfcisDict"]
        for sfciID,sfci in sfcisDict.items():
            assert sfci.sfciID == sfciID
            
            sloRealTimeValue = sfci.sloRealTimeValue
            assert sloRealTimeValue.availability >= 99.95
            assert sloRealTimeValue.latency <= 35
            assert sloRealTimeValue.throughput <= 0.1
            assert sloRealTimeValue.dropRate <= 100

            assert len(sfci.vnfiSequence) != 0
            vnfiSequence = sfci.vnfiSequence
            for vnfis in vnfiSequence:
                for vnfi in vnfis:
                    vnfiStatus = vnfi.vnfiStatus
                    assert type(vnfiStatus) == VNFIStatus
                    assert vnfiStatus.inputTrafficAmount["Direction1"] >= 0
                    assert vnfiStatus.inputTrafficAmount["Direction2"] >= 0
                    assert vnfiStatus.inputPacketAmount["Direction1"] >= 0
                    assert vnfiStatus.inputPacketAmount["Direction2"] >= 0
                    assert vnfiStatus.outputTrafficAmount["Direction1"] >= 0
                    assert vnfiStatus.outputTrafficAmount["Direction2"] >= 0
                    assert vnfiStatus.outputPacketAmount["Direction1"] >= 0
                    assert vnfiStatus.outputPacketAmount["Direction2"] >= 0
                    vnfType = vnfi.vnfType
                    if vnfType == VNF_TYPE_FW:
                        assert "FWRulesNum" in vnfiStatus.state
                        assert vnfiStatus.state["FWRulesNum"] == 2
                    elif vnfType == VNF_TYPE_MONITOR:
                        assert "FlowStatisticsDict" in vnfiStatus.state
                        assert type(vnfiStatus.state["FlowStatisticsDict"]) == dict
                    elif vnfType == VNF_TYPE_RATELIMITER:
                        assert "rateLimitition" in vnfiStatus.state
                        vnfiStatus.state["rateLimitition"] == 1
                    else:
                        raise ValueError("Unknown vnf type {0}".format(vnfType))
