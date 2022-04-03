#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid
import logging

import pytest

from sam.base.server import *
from sam.base.command import *
from sam.test.fixtures.orchestrationStub import OrchestrationStub
from sam.base.messageAgent import MessageAgent, SAMMessage
from sam.test.testBase import *
from sam.mediator.mediator import *
from sam.base.command import *

MANUAL_TEST = True

logging.basicConfig(level=logging.INFO)

class TestMediatorClass(TestBase):
    def setup_method(self, method):
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """
        self.mARecv = MessageAgent()
        self.mASend = MessageAgent()

    def teardown_method(self, method):
        """ teardown any state that was previously setup with a setup_method
        call.
        """

    # def test_isCommand(self):
    #     body = Command(1,2)
    #     assert self.mA.isCommand(body) == True
    #     body = 1
    #     assert self.mA.isCommand(body) == False

    # def test_isCommandReply(self):
    #     body = CommandReply(1,2)
    #     assert self.mA.isCommandReply(body) == True
    #     body = 1
    #     assert self.mA.isCommandReply(body) == False

    def test_requestMsgByRPC(self):
        self.mARecv.startMsgReceiverRPCServer("127.0.0.1", "49998")
        msg = {"a":1}
        samMsg = SAMMessage("TMP", msg)
        self.mASend.startMsgReceiverRPCServer("127.0.0.1", "49999")
        time.sleep(10)
        self.mASend.sendMsgByRPC("127.0.0.1", "49998", samMsg)
        newMsg = self.mARecv.getMsgByRPC("127.0.0.1", "49998")
        assert newMsg.getbody() == samMsg.getbody()
