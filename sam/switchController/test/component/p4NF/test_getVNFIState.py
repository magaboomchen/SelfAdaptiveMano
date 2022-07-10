#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is an example for writing unit test for p4 controller (test _getVNFIStateHandler)
The work flow:
    * Mediator sends ‘GET_VNFI_STATE command’ to p4 controller;
    * P4 controller processes the command and then send back a command reply to the mediator;
    * Cautions! You just need send back all VNFI state in a dict, e.g. {"vnfiID": {"vnfisStateDict":{}}}
    PS1:The ‘GET_VNFI_STATE command’ and the corresponding ‘GET_VNFI_STATE command reply’ have same cmdID;
    PS2: Class TestBase and IntTestBaseClass has many useful function;

Usage of this unit test:
    python -m pytest ./test_getVNFIState.py -s --disable-warnings
'''

from time import sleep

import pytest

from sam.base.command import CMD_STATE_SUCCESSFUL
from sam.base.messageAgent import P4CONTROLLER_QUEUE, MSG_TYPE_P4CONTROLLER_CMD, \
    MEDIATOR_QUEUE, TURBONET_ZONE
from sam.base.messageAgentAuxillary.msgAgentRPCConf import P4_CONTROLLER_IP, TEST_PORT
from sam.base.vnf import VNF_TYPE_FW, VNF_TYPE_MONITOR, VNF_TYPE_RATELIMITER
from sam.switchController.test.component.p4ControllerTestBase import TestP4ControllerBase

MANUAL_TEST = True


class TestGetVNFIStateClass(TestP4ControllerBase):
    @pytest.fixture(scope="function")
    def setup_getVNFIState(self):
        self.common_setup()

        sleep(1)
        yield
        # teardown
        pass

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_getVNFIState(self, setup_getVNFIState):
        # exercise
        self.exerciseAddSFCAndSFCI()

        self.startMsgAgentRPCReciever("localhost", TEST_PORT)
        self.getVNFIStateCmd = self.measurer.genCMDGetVNFIState()
        self.sendCmdByRPC("localhost", P4_CONTROLLER_IP,
                        MSG_TYPE_P4CONTROLLER_CMD,
                        self.getVNFIStateCmd)

        # verify
        self.verifyGetVNFIStateCmdRply()

    def verifyGetVNFIStateCmdRply(self):
        cmdRply = self.recvCmdRplyByRPC("localhost", TEST_PORT)
        assert cmdRply.cmdID == self.getVNFIStateCmd.cmdID
        assert "vnfisStateDict" in cmdRply.attributes
        assert type(cmdRply.attributes["vnfisStateDict"]) == dict
        assert len(cmdRply.attributes["vnfisStateDict"]) >= 0
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        assert cmdRply.attributes['zone'] == TURBONET_ZONE
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
