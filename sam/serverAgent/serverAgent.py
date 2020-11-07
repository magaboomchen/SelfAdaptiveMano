#!/usr/bin/python
# -*- coding: UTF-8 -*-

import pika
import sys
import base64
import time
import uuid
import os
import subprocess
import threading

import pickle

from sam.serverAgent.argParser import ArgParser
from sam.serverAgent.systemChecker import SystemChecker
from sam.serverAgent.bessStarter import BessStarter
from sam.serverAgent.dockerConfigurator import DockerConfigurator
from sam.serverAgent.dpdkConfigurator import DPDKConfigurator
from sam.base.server import Server
from sam.base.messageAgent import *
from sam.base.loggerConfigurator import LoggerConfigurator

HEAT_BEAT_TIME = 10


class ServerAgent(object):
    def __init__(self,controlNICName, serverType, datapathNICIP, NICPCIAddress):
        logConfigur = LoggerConfigurator(__name__, './log',
            'serverAgent.log', level='info')
        self.logger = logConfigur.getLogger()
        self.logger.info('Init ServerAgent')
        self._messageAgent = MessageAgent(self.logger)

        SystemChecker()
        DockerConfigurator().configDockerListenPort()

        self._server = Server(controlNICName, datapathNICIP, serverType)
        self._server.updateControlNICMAC()
        self._server.updateIfSet()

        self.grpcUrl = self._server.getControlNICIP() + ":10514"
        self.bS = BessStarter(self.grpcUrl)
        self.bS.killBessd() # must kill bessd first
        DPDKConfigurator(NICPCIAddress)
        self._server.updateDataPathNICMAC() # Then we can guarantee huge page
        self.bS.startBESSD()

    def run(self):
        self.logger.info("start server Agent routine")
        while True:
            # send server info to server controller
            self._server.updateIfSet()
            self._server.updateResource()
            self._sendServerInfo()
            time.sleep(HEAT_BEAT_TIME)

    def _sendServerInfo(self):
        msg = SAMMessage(MSG_TYPE_SERVER_REPLY, self._server)
        self.logger.debug(msg.getMessageID())
        self._messageAgent.sendMsg(SERVER_MANAGER_QUEUE,msg)


if __name__=="__main__":
    argParser = ArgParser()
    NICPCIAddress = argParser.getArgs()['nicPciAddress']   # example: 0000:00:08.0
    controllNICName = argParser.getArgs()['controllNicName']   # example: ens3
    serverType = argParser.getArgs()['serverType']   # example: vnfi, classifier
    datapathNICIP = argParser.getArgs()['datapathNicIP']   # example: 2.2.0.38

    serverAgent = ServerAgent(controllNICName, serverType, datapathNICIP, NICPCIAddress)
    serverAgent.run()
