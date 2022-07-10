#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is the test for p4controller and Turbonet

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
import logging

import pytest

from sam.base.command import Command, CMD_TYPE_ADD_NSH_ROUTE, \
        CMD_TYPE_DEL_NSH_ROUTE, CMD_TYPE_ADD_CLASSIFIER_ENTRY, CMD_TYPE_DEL_CLASSIFIER_ENTRY
from sam.base.messageAgent import MSG_TYPE_TURBONET_CONTROLLER_CMD, MessageAgent, SAMMessage
from sam.base.messageAgentAuxillary.msgAgentRPCConf import TURBONET_CONTROLLER_IP, \
                                                            TURBONET_CONTROLLER_PORT
from sam.switchController.test.component.p4ControllerTestBase import TestP4ControllerBase

MANUAL_TEST = True


class TestAddClassifierEntryClass(TestP4ControllerBase):
    @pytest.fixture(scope="function")
    def setup_addOrDelInboundClassifierEntry(self):
        # add 1 entry for the sam NSH (emulate 2 SFCI)
        self.messageAgent = MessageAgent()

        attr = {
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

        # To delete a entry, please use CMD_TYPE_DEL_CLASSIFIER_ENTRY instead
        cmd = Command(CMD_TYPE_ADD_CLASSIFIER_ENTRY, uuid.uuid1(),
                                                    attributes=attr)
        msg = SAMMessage(MSG_TYPE_TURBONET_CONTROLLER_CMD, cmd)
        self.tmpMessageAgent.sendMsgByRPC(TURBONET_CONTROLLER_IP, 
                                        TURBONET_CONTROLLER_PORT)

    @pytest.fixture(scope="function")
    def setup_addOrDelOutboundClassifierEntry(self):
        self.messageAgent = MessageAgent()

        attr = {
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

        # To delete a entry, please use CMD_TYPE_DEL_CLASSIFIER_ENTRY instead
        cmd = Command(CMD_TYPE_ADD_CLASSIFIER_ENTRY, uuid.uuid1(),
                                                    attributes=attr)
        msg = SAMMessage(MSG_TYPE_TURBONET_CONTROLLER_CMD, cmd)
        self.tmpMessageAgent.sendMsgByRPC(TURBONET_CONTROLLER_IP, 
                                        TURBONET_CONTROLLER_PORT)

    @pytest.fixture(scope="function")
    def setup_addOrDelSFCRouteEntry(self):
        self.messageAgent = MessageAgent()

        attr = {
            "match":{
                "etherType": 0x894F,
                "nsh": 0xFFFFFFFF       # NSH: 32bits
            },
            "action":{
                "nextNodeID": 10001     # serverID or switchID
            }
        }

        # To delete a entry, please use CMD_TYPE_DEL_NSH_ROUTE instead
        cmd = Command(CMD_TYPE_ADD_NSH_ROUTE, uuid.uuid1(),
                                                    attributes=attr)
        msg = SAMMessage(MSG_TYPE_TURBONET_CONTROLLER_CMD, cmd)
        self.tmpMessageAgent.sendMsgByRPC(TURBONET_CONTROLLER_IP, 
                                        TURBONET_CONTROLLER_PORT)
