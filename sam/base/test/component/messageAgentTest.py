import pika
import subprocess
import logging
import threading
import time
import ctypes
import inspect
import uuid
import base64
import pickle
import sys
from sam.base.messageAgent import *
# TODO: refactor, pytest
class SAMMessageTester(object):
    def __init__(self):
        samMsg = SAMMessage(MSG_TYPE_STRING,"apple")
        self._test(samMsg)

    def _test(self,samMsg):
        msgType = samMsg.getMessageType()
        logging.info(msgType)

        msgID = samMsg.getMessageID()
        logging.info(msgID)

        msgBody = samMsg.getbody()
        logging.info(msgBody)

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

if __name__=="__main__":
    logging.basicConfig(level=logging.INFO)
    SAMMessageTester()
    time.sleep(2)
    MessageAgentTester()