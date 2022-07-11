#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid

from sam.base.messageAgent import MessageAgent
from sam.base.command import CMD_TYPE_GET_FLOW_SET, CMD_TYPE_GET_VNFI_STATE, \
                            Command, CMD_TYPE_GET_SERVER_SET, \
                            CMD_TYPE_GET_TOPOLOGY, CMD_TYPE_GET_SFCI_STATE


class MeasurementStub(object):
    def __init__(self):
        self.mA = MessageAgent()
        # self.mA.startRecvMsg(ORCHESTRATOR_QUEUE)

    def genCMDGetServerSet(self):
        cmdID = uuid.uuid1()
        attr = {}
        cmd = Command(CMD_TYPE_GET_SERVER_SET, cmdID, attr)
        return cmd

    def genCMDGetTopo(self):
        cmdID = uuid.uuid1()
        attr = {}
        cmd = Command(CMD_TYPE_GET_TOPOLOGY, cmdID, attr)
        return cmd

    def genCMDGetSFCIState(self):
        cmdID = uuid.uuid1()
        attr = {}
        cmd = Command(CMD_TYPE_GET_SFCI_STATE, cmdID, attr)
        return cmd

    def genCMDGetVNFIState(self):
        cmdID = uuid.uuid1()
        attr = {}
        cmd = Command(CMD_TYPE_GET_VNFI_STATE, cmdID, attr)
        return cmd

    def genCMDGetFlowSet(self):
        cmdID = uuid.uuid1()
        attr = {}
        cmd = Command(CMD_TYPE_GET_FLOW_SET, cmdID, attr)
        return cmd

    def genCMDGetTopology(self):
        cmdID = uuid.uuid1()
        attr = {}
        cmd = Command(CMD_TYPE_GET_TOPOLOGY, cmdID, attr)
        return cmd