#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.messageAgent import SAMMessage, MessageAgent, \
    MSG_TYPE_SERVER_MANAGER_CMD_REPLY, MEDIATOR_QUEUE


class ServerManagerStub(object):
    def __init__(self):
        self.mA = MessageAgent()

    def sendCmdRply(self,cmdRply):
        msg = SAMMessage(MSG_TYPE_SERVER_MANAGER_CMD_REPLY, cmdRply)
        self.mA.sendMsg(MEDIATOR_QUEUE, msg)