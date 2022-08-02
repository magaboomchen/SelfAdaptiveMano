#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.messageAgent import DISPATCHER_QUEUE, MessageAgent


class DispatcherStub(object):
    def __init__(self):
        logConfigur = LoggerConfigurator(__name__, './log',
                                            'despatcherStub.log',
                                            level='debug')
        self.logger = logConfigur.getLogger()
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
                    self.logger.info("DispatcherStub: recvCmd")
                    return body
                else:
                    self.logger.error("Unknown massage body")
