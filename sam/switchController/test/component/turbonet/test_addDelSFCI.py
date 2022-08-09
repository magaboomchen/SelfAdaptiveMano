#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is the test for Turbonet Controller

Assume Turbonet Controller run MessageAgent():
    ip = TURBONET_CONTROLLER_IP
    port = TURBONET_CONTROLLER_PORT
    messageAgent.startMsgReceiverRPCServer(ip, port)

Usage of this unit test:
    python -m pytest ./test_addDelSFCI.py -s --disable-warnings

Reference:
https://datatracker.ietf.org/doc/html/rfc8300
'''

import uuid

import pytest

from sam.base.command import CMD_STATE_SUCCESSFUL, CMD_TYPE_DEL_CLASSIFIER_ENTRY, \
                        CMD_TYPE_DEL_NSH_ROUTE, Command, CMD_TYPE_ADD_NSH_ROUTE, \
                        CMD_TYPE_ADD_CLASSIFIER_ENTRY
from sam.base.messageAgent import MSG_TYPE_TURBONET_CONTROLLER_CMD, TURBONET_ZONE
from sam.base.messageAgentAuxillary.msgAgentRPCConf import TEST_PORT, TURBONET_CONTROLLER_IP, \
                                                            TURBONET_CONTROLLER_PORT
from sam.switchController.test.component.p4ControllerTestBase import TestP4ControllerBase


class TestAddClassifierEntryClass(TestP4ControllerBase):
    @pytest.fixture(scope="function")
    def setup_addAndDelInboundClassifierEntry(self):
        #setup
        # add 1 entry for the sam NSH (emulate 2 SFCI)
        self.startMsgAgentRPCReciever("localhost", TEST_PORT)

        self.attr = {
            "match":{
                "etherType": 0x0800,    # IPv4: 0x0800
                                        # IPv6: 0x86DD
                                        # RoceV1: 0x8915
                "dst": 0xFFFFFFFF       # IPv4: 32bits
                                        # IPv6: 128bits
                                        # SRv6: 128bits
                                        # RoceV1: 128bits
            },
            "action":{
                "encapsulateNSH": {
                    "SPI": 0xFFF,
                    "SI": 0xF,
                    "nextProtocol": 0x01,   # 0x1: IPv4
                                         # 0x2: IPv6
                                         # 0x3: Ethernet
                                         # 0x4: NSH
                                         # 0x5: MPLS
                                         # 0xFE: Experiment 1
                                         # 0xFF: Experiment 2
                    "MDType": 0x01
                }
            }
        }
        
        yield
        # teardown
        pass

    def test_addAndDelInboundClassifierEntry(self, 
                                        setup_addAndDelInboundClassifierEntry):
        
        self.turbonetAddDelEntryTest(
                                    CMD_TYPE_ADD_CLASSIFIER_ENTRY,
                                    CMD_TYPE_DEL_CLASSIFIER_ENTRY
                                    )

    @pytest.fixture(scope="function")
    def setup_addAndDelOutboundClassifierEntry(self):
        self.startMsgAgentRPCReciever("localhost", TEST_PORT)

        self.attr = {
            "match":{
                "etherType": 0x894F,
                "nsh": 0xFFFFFFFF       # NSH: 32bits
            },
            "action":{
                "decapsulateNSH": {
                    "newEtherType": 0x0800,    # IPv4: 0x0800
                                                # IPv6: 0x86DD
                                                # RoceV1: 0x8915
                }
            }
        }

        yield
        # teardown
        pass

    def test_addOrDelOutboundClassifierEntry(self, 
                                        setup_addAndDelOutboundClassifierEntry):
        
        self.turbonetAddDelEntryTest(
                                    CMD_TYPE_ADD_CLASSIFIER_ENTRY,
                                    CMD_TYPE_DEL_CLASSIFIER_ENTRY
                                    )

    @pytest.fixture(scope="function")
    def setup_addAndDelSFCRouteEntry(self):
        self.startMsgAgentRPCReciever("localhost", TEST_PORT)

        self.attr = {
            "match":{
                "etherType": 0x894F,
                "nsh": 0xFFFFFFFF       # NSH: 32bits
            },
            "action":{
                "nextNodeID": 10001     # serverID or switchID
            }
        }

        yield
        # teardown
        pass

    def test_addOrDelOutboundClassifierEntry(self, 
                                        setup_addAndDelSFCRouteEntry):
        
        self.turbonetAddDelEntryTest(
                                    CMD_TYPE_ADD_NSH_ROUTE,
                                    CMD_TYPE_DEL_NSH_ROUTE
                                    )

    def turbonetAddDelEntryTest(self, addCmdType, delCmdType):
        # exercise: add entry
        self.addClassifierEntryCmd = Command(addCmdType, uuid.uuid1(),
                                                    attributes=self.attr)
        self.sendCmdByRPC(TURBONET_CONTROLLER_IP, 
                        TURBONET_CONTROLLER_PORT,
                        MSG_TYPE_TURBONET_CONTROLLER_CMD,
                        self.addClassifierEntryCmd)

        # verify
        self.verifyAddClssifierEntryCmd()

        # exercise: delete entry
        self.delClassifierEntryCmd = Command(delCmdType, uuid.uuid1(),
                                                    attributes=self.attr)
        self.sendCmdByRPC(TURBONET_CONTROLLER_IP, 
                        TURBONET_CONTROLLER_PORT,
                        MSG_TYPE_TURBONET_CONTROLLER_CMD,
                        self.delClassifierEntryCmd)

        # verify
        self.verifyDelClssifierEntryCmd()

    def verifyAddClssifierEntryCmd(self):
        cmdRply = self.recvCmdRplyByRPC(TURBONET_CONTROLLER_IP, 
                                        TURBONET_CONTROLLER_PORT)
        assert cmdRply.cmdID == self.addClassifierEntryCmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        assert cmdRply.attributes['zone'] == TURBONET_ZONE

    def verifyDelClssifierEntryCmd(self):
        cmdRply = self.recvCmdRplyByRPC(TURBONET_CONTROLLER_IP, 
                                        TURBONET_CONTROLLER_PORT)
        assert cmdRply.cmdID == self.delClassifierEntryCmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        assert cmdRply.attributes['zone'] == TURBONET_ZONE
