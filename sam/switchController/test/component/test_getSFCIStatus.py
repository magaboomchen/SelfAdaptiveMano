#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is an example for writing unit test for p4 controller (test _getSFCIStatusHandler)
The work flow:
    * Mediator sends ‘GET_SFCI_Status command’ to p4 controller;
    * P4 controller processes the command and then send back a command reply to the mediator;
    * Cautions! You just need send back all SFCI objects in a dict, e.g. {"sfciID": SFCI()}
    * We should check whether variable in SFCI object has been updated.
    PS1:The ‘GET_SFCI_Status command’ and the corresponding ‘GET_SFCI_Status command reply’ have same cmdID;
    PS2: Class TestBase and IntTestBaseClass has many useful function;

Usage of this unit test:
    python -m pytest ./test_getSFCIStatus.py -s --disable-warnings
'''

from time import sleep

import pytest

from sam.base.command import CMD_STATE_SUCCESSFUL
from sam.base.messageAgent import MEDIATOR_QUEUE, MSG_TYPE_P4CONTROLLER_CMD, P4CONTROLLER_QUEUE, TURBONET_ZONE
from sam.base.messageAgentAuxillary.msgAgentRPCConf import P4_CONTROLLER_IP, TEST_PORT
from sam.base.vnf import VNF_TYPE_FW, VNF_TYPE_MONITOR, VNF_TYPE_RATELIMITER
from sam.switchController.test.component.p4ControllerTestBase import TestP4ControllerBase

MANUAL_TEST = True


class TestGetSFCIStatusClass(TestP4ControllerBase):
    @pytest.fixture(scope="function")
    def setup_getSFCIStatus(self):
        self.common_setup()

        sleep(1)
        yield
        # teardown
        pass

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_getSFCIStatus(self, setup_getSFCIStatus):
        # exercise
        self.exerciseAddSFCAndSFCI()

        self.startMsgAgentRPCReciever("localhost", TEST_PORT)
        self.getSFCIStatusCmd = self.measurer.genCMDGetSFCIStatus()
        self.sendCmdByRPC("localhost", P4_CONTROLLER_IP,
                        MSG_TYPE_P4CONTROLLER_CMD,
                        self.getSFCIStatusCmd)

        # verify
        self.verifyGetSFCIStatusCmdRply()



    def verifyGetSFCIStatusCmdRply(self):
        cmdRply = self.recvCmdRplyByRPC("localhost", TEST_PORT)
        assert cmdRply.cmdID == self.getSFCIStatusCmd.cmdID
        assert "sfcisDict" in cmdRply.attributes
        assert type(cmdRply.attributes["sfcisDict"]) == dict
        assert len(cmdRply.attributes["sfcisDict"]) >= 0
        assert cmdRply.cmdStatus == CMD_STATE_SUCCESSFUL
        assert cmdRply.attributes['zone'] == TURBONET_ZONE
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
