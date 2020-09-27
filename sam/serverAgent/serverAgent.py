#!/usr/bin/python
# -*- coding: UTF-8 -*-

import pika
import sys
import base64
import time
import uuid
import os
import subprocess
import logging
import threading

import pickle

from sam.serverAgent.argParser import ArgParser
from sam.serverAgent.systemChecker import SystemChecker
from sam.serverAgent.dpdkConfigurator import DPDKConfigurator
from sam.serverAgent.bessStarter import BessStarter
from sam.serverAgent.dockerConfigurator import DockerConfigurator
from sam.base.server import Server
from sam.base.messageAgent import *

HEAT_BEAT_TIME = 10

class ServerAgent(object):
    def __init__(self,controlNICName, serverType, datapathNICIP):
        logging.info('Init ServerAgent')
        self._server = Server(controlNICName, datapathNICIP, serverType)
        self._server.updateControlNICMAC()
        self._server.updateDataPathNICMAC()
        self._messageAgent = MessageAgent()

    def run(self):
        while True:
            # send server info to server controller
            self._server.updateIfSet()
            self._server.updateResource()
            self._sendServerInfo()
            time.sleep(HEAT_BEAT_TIME)

    def _sendServerInfo(self):
        msg = SAMMessage(MSG_TYPE_SERVER_REPLY, self._server)
        logging.debug(msg.getMessageID())
        self._messageAgent.sendMsg(SERVER_MANAGER_QUEUE,msg)

if __name__=="__main__":
    logging.basicConfig(level=logging.INFO)

    argParser = ArgParser()
    NICPCIAddress = argParser.getArgs()['nicPciAddress']   # example: 0000:00:08.0
    controllNICName = argParser.getArgs()['controllNicName']   # example: ens3
    serverType = argParser.getArgs()['serverType']   # example: vnfi, classifier
    datapathNICIP = argParser.getArgs()['datapathNicIP']   # example: 2.2.0.38

    SystemChecker()

    DockerConfigurator().configDockerListenPort()

    DPDKConfigurator(NICPCIAddress)

    serverAgent = ServerAgent(controllNICName, serverType, datapathNICIP)
    BessStarter()
    serverAgent.run()