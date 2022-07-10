#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is the component test for simulator (test _getVNFIStateHandler)
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
from sam.base.messageAgentAuxillary.msgAgentRPCConf import SIMULATOR_PORT, TEST_PORT
from sam.base.shellProcessor import ShellProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.vnf import VNF_TYPE_FW, VNF_TYPE_MONITOR, VNF_TYPE_RATELIMITER
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.test.fixtures.measurementStub import MeasurementStub
from sam.simulator.test.testSimulatorBase import TestSimulatorBase
from sam.simulator import simulator
from sam.test.testBase import CLASSIFIER_DATAPATH_IP

MANUAL_TEST = True


class TestGetVNFIStateClass(TestSimulatorBase):
    def common_setup(self):
        logConfigur = LoggerConfigurator(__name__, './log',
                                        'testGetVNFIStateClass.log',
                                        level='debug')
        self.logger = logConfigur.getLogger()
        self.logger.setLevel(logging.DEBUG)

        # setup
        self.sP = ShellProcessor()
        self.cleanLog()
        self.clearQueue()
        self.killAllModule()
        self.mediator = MediatorStub()
        self.measurer = MeasurementStub()

        self.sfcList = []
        self.sfciList = []
        self.serverBasedClassifier = False

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
        self.addSFCI2Simulator()
        self.startMsgAgentRPCReciever("localhost", TEST_PORT)

        self.getVNFIStateCmd = self.measurer.genCMDGetVNFIState()
        self.sendCmdByRPC("localhost", SIMULATOR_PORT,
                        MSG_TYPE_SIMULATOR_CMD,
                        self.getVNFIStateCmd)

        # verify
        self.verifyGetVNFIStateCmdRply()

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

    def verifyGetVNFIStateCmdRply(self):
        cmdRply = self.recvCmdRplyByRPC("localhost", TEST_PORT)
        assert cmdRply.cmdID == self.getVNFIStateCmd.cmdID
        assert "vnfisStateDict" in cmdRply.attributes
        assert type(cmdRply.attributes["vnfisStateDict"]) == dict
        assert len(cmdRply.attributes["vnfisStateDict"]) >= 0
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        assert cmdRply.attributes['zone'] == SIMULATOR_ZONE
        vnfisStateDict = cmdRply.attributes["vnfisStateDict"]
        for vnfiID,contentDict in vnfisStateDict.items():
            assert "vnfType" in contentDict
            vnfType = contentDict["vnfType"]
            if vnfType == VNF_TYPE_FW:
                assert "FWRulesNum" in contentDict
                assert contentDict["FWRulesNum"] == 2
            elif vnfType == VNF_TYPE_MONITOR:
                assert "FlowStatisticsDict" in contentDict
                assert type(contentDict["FlowStatisticsDict"]) == dict
            elif vnfType == VNF_TYPE_RATELIMITER:
                assert "rateLimitition" in contentDict
                contentDict["rateLimitition"] == 1
            else:
                raise ValueError("Unknown vnf type {0}".format(vnfType))
