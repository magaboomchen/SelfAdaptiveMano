#!/usr/bin/env python
import pika
import sys
import base64
import pickle
import time
import uuid
import os
import subprocess
import logging
import Queue
import threading
from argParser import ArgParser
from systemChecker import SystemChecker
from dpdkConfigure import DPDKConfigurator
from bessStarter import BessStarter
from server import Server
sys.path.append("../Message")
from messageAgent import *

HEAT_BEAT_TIME = 10

class ServerAgent():
    def __init__(self,controlNICName):
        logging.info('Init ServerAgent')
        self._server = Server(controlNICName)
        self._messageAgent = MessageAgent()

    def run(self):
        while True:
            # send server info to server controller
            self._server.updateIfSet()
            self._sendServerInfo()
            time.sleep(HEAT_BEAT_TIME)

    def _sendServerInfo(self):
        msg = SAMMessage(MSG_TYPE_SERVER, self._server)
        logging.debug(msg.getMessageID())
        self._messageAgent.sendMsg(SERVER_MANAGER_QUEUE,msg)


if __name__=="__main__":
    logging.basicConfig(level=logging.INFO)

    argParser = ArgParser()
    NICPCIAddress = argParser.getArgs()['nicPciAddress']   # example: 0000:00:08.0
    ControllNICName = argParser.getArgs()['controllNicName']   # example: ens3

    SystemChecker()
    DPDKConfigurator(NICPCIAddress)
    BessStarter()

    serverAgent = ServerAgent(ControllNICName)
    serverAgent.run()