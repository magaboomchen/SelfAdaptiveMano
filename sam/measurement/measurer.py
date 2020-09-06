#!/usr/bin/python
# -*- coding: UTF-8 -*-

import base64
import time
import uuid
import subprocess
import logging
import struct
import copy

import pickle

from sam.base.server import Server
from sam.base.messageAgent import *
from sam.base.switch import *
from sam.base.sfc import *
from sam.base.command import *


class Measurer(object):
    def __init__(self):
        self.serverSet = {}
        self.switches = {}
        self.links = {}
        self.hosts = {}
        self.vnfis = {}

        self._messageAgent = MessageAgent()
        self._messageAgent.startRecvMsg(MEASURER_QUEUE)

    def startMeasurer(self):
        while True:
            msg = self._messageAgent.getMsg(MEASURER_QUEUE)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            else:
                body = msg.getbody()
                if self._messageAgent.isCommand(body):
                    self._commandHandler(body)
                elif self._messageAgent.isCommandReply(body):
                    self._commandReplyHandler(body)
                else:
                    loggind.error("Unknown massage body")


if __name__=="__main__":
    logging.basicConfig(level=logging.INFO)
    m = Measurer()
    m.startMeasurer()

