#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.messageAgent import *
from sam.base.command import *
from sam.base.sfc import *
from sam.base.vnf import *


class OrchestrationStub(object):
    def __init__(self):
        self.mA = MessageAgent()

    def genCMDAddSFCI(self,sfc,sfci):
        cmdID = uuid.uuid1()
        attr = {'sfc':sfc, 'sfci':sfci, 'sfcUUID':sfc.sfcUUID}
        cmd = Command(CMD_TYPE_ADD_SFCI, cmdID, attr)
        return cmd

    def genCMDDelSFCI(self,sfc,sfci):
        cmdID = uuid.uuid1()
        attr = {'sfc':sfc, 'sfci':sfci,'sfcUUID':sfc.sfcUUID}
        cmd = Command(CMD_TYPE_DEL_SFCI, cmdID, attr)
        return cmd

    def genCMDGetServer(self):
        cmdID = uuid.uuid1()
        cmd = Command(CMD_TYPE_GET_SERVER_SET, cmdID)
        return cmd

    def genCMDGetTopo(self):
        cmdID = uuid.uuid1()
        cmd = Command(CMD_TYPE_GET_TOPOLOGY, cmdID)
        return cmd

    def genCMDGetSFCI(self,sfc,sfci):
        cmdID = uuid.uuid1()
        attr = {'sfci':sfci, 'sfcUUID':sfc.sfcUUID}
        cmd = Command(CMD_TYPE_GET_SFCI_STATE, cmdID, attr)
        return cmd

    def startRecv(self):
        self.mA.startRecvMsg(ORCHESTRATOR_QUEUE)

    def recvCmdRply(self):
        while True:
            msg = self.mA.getMsg(ORCHESTRATOR_QUEUE)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            else:
                body = msg.getbody()
                if self.mA.isCommandReply(body):
                    logging.info("OrchestrationStub: recvCmdRply")
                    return body
                else:
                    logging.error("Unknown massage body")
