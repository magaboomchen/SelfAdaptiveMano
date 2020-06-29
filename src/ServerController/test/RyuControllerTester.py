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
import datetime
import sys
import ctypes
import inspect
sys.path.append("../../ServerAgent")
from messageAgent import *
from messageAgent import SAMMessage,MessageAgent
from server import Server

class RyuControllerTester():
    def __init__(self):
        logging.info('Init RyuControllerTester')
        self._messageAgent = MessageAgent()

    def sendCmdtoRyu(self,ryuCmdTable):
        msg = SAMMessage(MSG_TYPE_RYUCMD,ryuCmdTable)
        self._messageAgent.sendMsg(RYU_CONTROLLER_QUEUE,msg)

    def genRyuInstallationCmdTable(self):
        # body: items
        # item 1: 
        return 111

    def genRyuDeletionCmdTable(self):
        # body: items
        # item 1:
        return 222

if __name__=="__main__":
    logging.basicConfig(level=logging.info)
    ryuControllerTester = RyuControllerTester()
    while True:
        userCmd = raw_input(
            "please input user command.\n \
            install: start install sfc in ryu\n \
            del: to delete sfc in ryu\n \
            \
            Your input is:"
            )
        if userCmd == "install":
            logging.info("start install sfc in Ryu")
            RyuCmdTable = ryuControllerTester.genRyuInstallationCmdTable()
            ryuControllerTester.sendCmdtoRyuController(RyuCmdTable)
        elif userCmd == "del":
            logging.info("start delete sfc in Ryu")
            RyuCmdTable = ryuControllerTester.genRyuDeletionCmdTable()
            ryuControllerTester.sendCmdtoRyuController(RyuCmdTable)
        else:
            logging.warning("Unknown input.")