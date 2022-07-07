#!/usr/bin/python
# -*- coding: UTF-8 -*-

import time
import logging

from sam.test.testBase import TestBase
from sam.base.messageAgent import TEST_QUEUE, MessageAgent, SAMMessage

MANUAL_TEST = True

logging.basicConfig(level=logging.INFO)


class TestMessageAgentClass(TestBase):
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
        msg = {"a":1,"b":2,"c":3,"d":4}
        samMsg = SAMMessage("Test", msg)
        self.mASend.startMsgReceiverRPCServer("127.0.0.1", "49999")
        time.sleep(2)
        t1 = time.time()
        self.mASend.sendMsgByRPC("127.0.0.1", "49998", samMsg)
        newMsg = self.mARecv.getMsgByRPC("127.0.0.1", "49998")
        t2 = time.time()
        logging.info("time is {0}".format(t2-t1))
        assert newMsg.getbody() == samMsg.getbody()

    def test_requestMsgByRabbitMQ(self):
        self.mARecv.startRecvMsg("TEST_RECV_QUEUE")
        msg = {"a":1,"b":2,"c":3,"d":4}
        samMsg = SAMMessage("Test", msg)
        self.mASend.startRecvMsg("TEST_SEND_QUEUE")
        time.sleep(2)
        t1 = time.time()
        self.mASend.sendMsg("TEST_RECV_QUEUE", samMsg)
        while True:
            newMsg = self.mARecv.getMsg("TEST_RECV_QUEUE")
            if newMsg!=None:
                t2 = time.time()
                logging.info("time is {0}".format(t2-t1))
                assert newMsg.getbody() == samMsg.getbody()
                break
