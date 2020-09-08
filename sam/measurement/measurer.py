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
from sam.measurement.dcnInfoBaseMaintainer import *

# TODO: get topology, get server sets, get sfci status, database agent


class Measurer(object):
    def __init__(self):
        self.dib = DCNInfoBaseMaintainer()

        self._messageAgent = MessageAgent()
        self.queueName = self._messageAgent.genQueueName(MEASURER_QUEUE)
        self._messageAgent.startRecvMsg(self.queueName)

        logging.info("self.queueName:{0}".format(self.queueName))

    def startMeasurer(self):
        while True:
            msg = self._messageAgent.getMsg(self.queueName)
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
                    logging.error("Unknown massage body")

    def _commandReplyHandler(self, cmdRply):
        for key,values in cmdRply.attributes.items():
            if key == "servers":
                print("Get servers")
                self.hosts = values
            elif key == "switches":
                print("Get switches")
                self.switches = values
            elif key == "links":
                print("Get links")
                self.links = values
            else:
                print("Unknown command attributes {0}".format(key))


if __name__=="__main__":
    logging.basicConfig(level=logging.INFO)
    m = Measurer()
    m.startMeasurer()

