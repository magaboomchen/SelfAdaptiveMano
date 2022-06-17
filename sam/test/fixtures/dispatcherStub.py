#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging

from sam.base.messageAgent import DISPATCHER_QUEUE, MessageAgent
from sam.base.command import Command, CMD_TYPE_GET_SERVER_SET, \
    CMD_TYPE_GET_TOPOLOGY, CMD_TYPE_GET_SFCI_STATE


class DispatcherStub(object):
    def __init__(self):
        self.mA = MessageAgent()

    def startRecv(self):
        self.mA.startRecvMsg(DISPATCHER_QUEUE)

    def recvCmd(self):
        while True:
            msg = self.mA.getMsg(DISPATCHER_QUEUE)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            else:
                body = msg.getbody()
                if self.mA.isCommand(body):
                    logging.info("DispatcherStub: recvCmd")
                    return body
                else:
                    logging.error("Unknown massage body")
