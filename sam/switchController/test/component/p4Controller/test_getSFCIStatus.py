#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is an example for writing unit test for p4 controller (test _getSFCIStatusHandler)
The work flow:
    * Mediator sends 'GET_SFCI_Status command' to p4 controller;
    * P4 controller processes the command and then send back a command reply to the mediator;
    * Cautions! You just need send back all SFCI objects in a dict, e.g. {"sfciID": SFCI()}
    * We should check whether variable in SFCI object has been updated.
    PS1:The 'GET_SFCI_Status command' and the corresponding 'GET_SFCI_Status command reply' have same cmdID;
    PS2: Class TestBase and IntTestBaseClass has many useful function;

Usage of this unit test:
    python -m pytest ./test_getSFCIStatus.py -s --disable-warnings
'''

import datetime
from typing import Dict

import pytest

from sam.base.acl import ACLTable
from sam.base.command import CMD_STATE_SUCCESSFUL
from sam.base.messageAgent import MSG_TYPE_P4CONTROLLER_CMD, TURBONET_ZONE
from sam.base.messageAgentAuxillary.msgAgentRPCConf import P4_CONTROLLER_IP, P4_CONTROLLER_PORT, TEST_PORT
from sam.base.monitorStatistic import MonitorStatistics
from sam.base.rateLimiter import RateLimiterConfig
from sam.base.routingMorphic import IPV4_ROUTE_PROTOCOL, IPV6_ROUTE_PROTOCOL, \
                                    ROCEV1_ROUTE_PROTOCOL, SRV6_ROUTE_PROTOCOL
from sam.base.sfc import SFCI
from sam.base.sfcConstant import SFC_DIRECTION_0, SFC_DIRECTION_1
from sam.base.vnfiStatus import VNFIStatus
from sam.base.vnf import VNF_TYPE_FW, VNF_TYPE_MONITOR, VNF_TYPE_RATELIMITER
from sam.switchController.test.component.p4ControllerTestBase import TestP4ControllerBase


class TestGetSFCIStatusClass(TestP4ControllerBase):
    @pytest.fixture(scope="function")
    def setup_getSFCIStatus(self):
        self.common_setup()
        self.logger.info("Deploying SFCI to P4 controller.")
        self.exerciseAddSFCAndSFCI()
        self.logger.info("Deploying SFCI to P4 controller finish.")

        yield
        # teardown
        pass

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_getSFCIStatus(self, setup_getSFCIStatus):
        # exercise
        self.logger.info("Getting SFCI status from P4 controller finish.")
        self.startMsgAgentRPCReciever("localhost", TEST_PORT)
        self.getSFCIStateCmd = self.measurer.genCMDGetSFCIState()
        self.sendCmdByRPC(P4_CONTROLLER_IP, P4_CONTROLLER_PORT,
                        MSG_TYPE_P4CONTROLLER_CMD,
                        self.getSFCIStateCmd)

        # verify
        self.verifyGetSFCIStatusCmdRply()

    def verifyGetSFCIStatusCmdRply(self):
        cmdRply = self.recvCmdRplyByRPC("localhost", TEST_PORT)
        assert cmdRply.cmdID == self.getSFCIStateCmd.cmdID
        assert "sfcisDict" in cmdRply.attributes
        assert type(cmdRply.attributes["sfcisDict"]) == dict
        assert len(cmdRply.attributes["sfcisDict"]) >= 0
        assert cmdRply.cmdStatus == CMD_STATE_SUCCESSFUL
        assert cmdRply.attributes['zone'] == TURBONET_ZONE
        sfcisDict = cmdRply.attributes["sfcisDict"] # type: Dict[int, SFCI]
        for sfciID,sfci in sfcisDict.items():
            assert sfci.sfciID == sfciID

            # sloRealTimeValue = sfci.sloRealTimeValue
            # assert sloRealTimeValue.availability >= 99.95
            # assert sloRealTimeValue.latency <= 35
            # assert sloRealTimeValue.throughput <= 0.1
            # assert sloRealTimeValue.dropRate <= 100

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
                    assert type(vnfiStatus.timestamp) == datetime.datetime
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
