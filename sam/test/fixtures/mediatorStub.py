#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid

from sam.base.messageAgent import MessageAgent
from sam.base.command import CMD_TYPE_GET_SFCI_STATE, CMD_TYPE_GET_VNFI_STATE, Command, CMD_TYPE_ADD_SFC, \
    CMD_TYPE_ADD_SFCI, CMD_TYPE_DEL_SFCI, CMD_TYPE_DEL_SFC, \
    CMD_TYPE_GET_SERVER_SET, CMD_TYPE_GET_TOPOLOGY, CMD_TYPE_GET_FLOW_SET
from sam.test.fixtures.orchestrationStub import OrchestrationStub


class MediatorStub(OrchestrationStub):
    def __init__(self):
        self.mA = MessageAgent()

    def genCMDAddSFC(self,sfc):
        cmdID = uuid.uuid1()
        attr = {'sfc':sfc}
        cmd = Command(CMD_TYPE_ADD_SFC,cmdID,attr)
        return cmd

    def genCMDAddSFCI(self,sfc,sfci):
        cmdID = uuid.uuid1()
        attr = {'sfc':sfc,'sfci':sfci}
        cmd = Command(CMD_TYPE_ADD_SFCI,cmdID,attr)
        return cmd

    def genCMDDelSFCI(self,sfc,sfci):
        cmdID = uuid.uuid1()
        attr = {'sfc':sfc,'sfci':sfci}
        cmd = Command(CMD_TYPE_DEL_SFCI,cmdID,attr)
        return cmd

    def genCMDDelSFC(self,sfc):
        cmdID = uuid.uuid1()
        attr = {'sfc':sfc}
        cmd = Command(CMD_TYPE_DEL_SFC,cmdID,attr)
        return cmd

    def genCMDGetTopology(self):
        cmdID = uuid.uuid1()
        attr = {}
        cmd = Command(CMD_TYPE_GET_TOPOLOGY, cmdID, attr)
        return cmd

    def genCMDGetServerSet(self):
        cmdID = uuid.uuid1()
        attr = {}
        cmd = Command(CMD_TYPE_GET_SERVER_SET, cmdID, attr)
        return cmd

    def genCMDGetFlowSet(self):
        cmdID = uuid.uuid1()
        attr = {}
        cmd = Command(CMD_TYPE_GET_FLOW_SET, cmdID, attr)
        return cmd

    def genCMDGetVNFIState(self):
        cmdID = uuid.uuid1()
        attr = {}
        cmd = Command(CMD_TYPE_GET_VNFI_STATE, cmdID, attr)
        return cmd
