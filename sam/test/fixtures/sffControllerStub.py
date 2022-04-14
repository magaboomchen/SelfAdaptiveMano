#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.messageAgent import SAMMessage, MessageAgent, MEDIATOR_QUEUE, \
    MSG_TYPE_SFF_CONTROLLER_CMD_REPLY


class SFFControllerStub(object):
    def __init__(self):
        self.mA = MessageAgent()

    def sendCmdRply(self,cmdRply):
        msg = SAMMessage(MSG_TYPE_SFF_CONTROLLER_CMD_REPLY, cmdRply)
        self.mA.sendMsg(MEDIATOR_QUEUE, msg)