#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.messageAgent import SAMMessage, MessageAgent, SERVER_CLASSIFIER_CONTROLLER_QUEUE, \
    MSG_TYPE_CLASSIFIER_CONTROLLER_CMD_REPLY, MEDIATOR_QUEUE


class ClassifierControllerStub(object):
    def __init__(self):
        self.queue = SERVER_CLASSIFIER_CONTROLLER_QUEUE
        self.mA = MessageAgent()
        # self.mA.startRecvMsg(self.queue)

    def sendCmdRply(self, cmdRply):
        msg = SAMMessage(MSG_TYPE_CLASSIFIER_CONTROLLER_CMD_REPLY, cmdRply)
        self.mA.sendMsg(MEDIATOR_QUEUE, msg)