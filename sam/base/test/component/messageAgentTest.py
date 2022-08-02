#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging
import time
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.messageAgent import SAMMessage, MessageAgent, \
    MSG_TYPE_STRING

# TODO: refactor, pytest


class SAMMessageTester(object):
    def __init__(self):
        logConfigur = LoggerConfigurator(__name__, './log',
            'samMessageTester.log', level='warning')
        self.logger = logConfigur.getLogger()
        samMsg = SAMMessage(MSG_TYPE_STRING, "apple")
        self._test(samMsg)

    def _test(self,samMsg):
        msgType = samMsg.getMessageType()
        self.logger.info(msgType)

        msgID = samMsg.getMessageID()
        self.logger.info(msgID)

        msgBody = samMsg.getbody()
        self.logger.info(msgBody)

class MessageAgentTester(object):
    def __init__(self):
        messageAgent = MessageAgent()
        self._testSimulSendAndRecv(messageAgent)

    def _testSimulSendAndRecv(self,messageAgent):
        messageAgent.startRecvMsg("task_queue")
        while True:
            time.sleep(2)
            messageAgent.sendMsg("task_queue","HelloWor ld")
            time.sleep(2)
            msg = messageAgent.getMsg("task_queue")

            break
        
        print("Finish!")

if __name__=="__main__":
    SAMMessageTester()
    time.sleep(2)
    MessageAgentTester()