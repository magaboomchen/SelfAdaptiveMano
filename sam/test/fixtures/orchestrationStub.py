#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid

from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.messageAgent import TURBONET_ZONE, MessageAgent, ORCHESTRATOR_QUEUE
from sam.base.command import Command, CMD_TYPE_GET_SERVER_SET,\
    CMD_TYPE_ADD_SFCI, CMD_TYPE_DEL_SFCI, CMD_TYPE_GET_TOPOLOGY, \
        CMD_TYPE_GET_SFCI_STATE


class OrchestrationStub(object):
    def __init__(self):
        logConfigur = LoggerConfigurator(__name__, './log',
                                            'orchestratorStub.log',
                                            level='debug')
        self.logger = logConfigur.getLogger()
        self.mA = MessageAgent()

    def genCMDAddSFCI(self,sfc,sfci,source=None,zone=TURBONET_ZONE):
        cmdID = uuid.uuid1()
        attr = {'sfc':sfc, 'sfci':sfci, 'sfcUUID':sfc.sfcUUID,'zone':zone}
        cmd = Command(CMD_TYPE_ADD_SFCI, cmdID, attr)
        cmd.attributes['source'] = source
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
                    self.logger.info("OrchestrationStub: recvCmdRply")
                    return body
                else:
                    self.logger.error("Unknown massage body")
