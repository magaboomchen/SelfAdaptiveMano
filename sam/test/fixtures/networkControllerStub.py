#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.messageAgent import SAMMessage, MessageAgent, \
    MSG_TYPE_NETWORK_CONTROLLER_CMD_REPLY, MEDIATOR_QUEUE


class NetworkControllerStub(object):
    def __init__(self):
        self.mA = MessageAgent()
        # self.mA.startRecvMsg(NETWORK_CONTROLLER_QUEUE)
    
    def sendCmdRply(self,cmdRply):
        msg = SAMMessage(MSG_TYPE_NETWORK_CONTROLLER_CMD_REPLY, cmdRply)
        self.mA.sendMsg(MEDIATOR_QUEUE, msg)