#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is the component test for simulator (test _getSFCIStatusHandler)
The work flow:
    * Mediator sends 'GET_SFCI_Status command' to simulator;
    * Simulator processes the command and then send back a command reply to the mediator;
    * Cautions! You just need send back all SFCI objects in a dict, e.g. {"sfciID": SFCI()}
    * We should check whether variable in SFCI object has been updated.
    PS1:The 'GET_SFCI_Status command' and the corresponding 'GET_SFCI_Status command reply' have same cmdID;
    PS2: Class TestBase and TestSimulatorBase has many useful function;

Usage of this unit test:
    python -m pytest ./sam/simulator/test/test_getSFCIStatus.py -s --disable-warnings
'''

from time import sleep

import pytest

from sam.base.acl import ACLTable
from sam.base.monitorStatistic import MonitorStatistics
from sam.base.command import CMD_STATE_SUCCESSFUL
from sam.base.messageAgent import SIMULATOR_QUEUE, MSG_TYPE_SIMULATOR_CMD, \
    MEDIATOR_QUEUE, SIMULATOR_ZONE
from sam.base.messageAgentAuxillary.msgAgentRPCConf import SIMULATOR_PORT, TEST_PORT
from sam.base.routingMorphic import IPV4_ROUTE_PROTOCOL, IPV6_ROUTE_PROTOCOL, ROCEV1_ROUTE_PROTOCOL, SRV6_ROUTE_PROTOCOL
from sam.base.sfc import SFC_DIRECTION_0, SFC_DIRECTION_1
from sam.base.rateLimiter import RateLimiterConfig
from sam.base.shellProcessor import ShellProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.vnf import VNF_TYPE_FW, VNF_TYPE_MONITOR, VNF_TYPE_RATELIMITER, VNFIStatus
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.test.fixtures.measurementStub import MeasurementStub
from sam.simulator.test.testSimulatorBase import TestSimulatorBase
from sam.simulator import simulator
from sam.test.testBase import CLASSIFIER_DATAPATH_IP


class TestGetSFCIStatusClass(TestSimulatorBase):
    def common_setup(self):
        logConfigur = LoggerConfigurator(__name__, './log',
                                        'testGetSFCIStatusClass.log',
                                        level='debug')
        self.logger = logConfigur.getLogger()

        # setup
        self.sP = ShellProcessor()
        self.cleanLog()
        self.clearQueue()
        self.killAllModule()
        self.dropRequestAndSFCAndSFCITableInDB()
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

        self.getSFCIStateCmd = self.measurer.genCMDGetSFCIState()
        self.sendCmdByRPC("localhost", SIMULATOR_PORT,
                        MSG_TYPE_SIMULATOR_CMD,
                        self.getSFCIStateCmd)

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
            self.logger.info("test idx {0}".format(idx))
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
        assert cmdRply.cmdID == self.getSFCIStateCmd.cmdID
        assert "sfcisDict" in cmdRply.attributes
        assert type(cmdRply.attributes["sfcisDict"]) == dict
        assert len(cmdRply.attributes["sfcisDict"]) >= 0
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        assert cmdRply.attributes['zone'] == SIMULATOR_ZONE
        sfcisDict = cmdRply.attributes["sfcisDict"]
        for sfciID,sfci in sfcisDict.items():
            # type: Dict[int, SFCI]
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
                    assert vnfiStatus.inputTrafficAmount[SFC_DIRECTION_0] >= 0
                    assert vnfiStatus.inputTrafficAmount[SFC_DIRECTION_1] >= 0
                    assert vnfiStatus.inputPacketAmount[SFC_DIRECTION_0] >= 0
                    assert vnfiStatus.inputPacketAmount[SFC_DIRECTION_1] >= 0
                    assert vnfiStatus.outputTrafficAmount[SFC_DIRECTION_0] >= 0
                    assert vnfiStatus.outputTrafficAmount[SFC_DIRECTION_1] >= 0
                    assert vnfiStatus.outputPacketAmount[SFC_DIRECTION_0] >= 0
                    assert vnfiStatus.outputPacketAmount[SFC_DIRECTION_1] >= 0
                    vnfType = vnfi.vnfType
                    if vnfType == VNF_TYPE_FW:
                        assert type(vnfiStatus.state) == ACLTable
                        assert vnfiStatus.state.getRulesNum(IPV4_ROUTE_PROTOCOL) == 2
                    elif vnfType == VNF_TYPE_MONITOR:
                        assert type(vnfiStatus.state) == MonitorStatistics
                        for directionID in [SFC_DIRECTION_0, SFC_DIRECTION_1]:
                            for routeProtocol in [IPV4_ROUTE_PROTOCOL, IPV6_ROUTE_PROTOCOL,
                                                    SRV6_ROUTE_PROTOCOL, ROCEV1_ROUTE_PROTOCOL]:
                                self.logger.info("MonitorStatistics is {0}".format(
                                    vnfiStatus.state.getPktBytesRateStatisticDict(directionID, routeProtocol)))
                    elif vnfType == VNF_TYPE_RATELIMITER:
                        assert type(vnfiStatus.state) == RateLimiterConfig
                        assert vnfiStatus.state.maxMbps == 100
                    else:
                        raise ValueError("Unknown vnf type {0}".format(vnfType))
