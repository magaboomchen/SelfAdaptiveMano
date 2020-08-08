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
from sam.base.messageAgent import *
from sam.base.server import *
# TODO: refactor, pytest
class ServerTester(object):
    def __init__(self,controlIfName):
        server = Server(controlIfName, "2.2.122.222", SERVER_TYPE_NORMAL)

        server.updateIfSet()

        ifset = server.getIfSet()
        logging.info(ifset)

        server.printIfSet()

        controlNICMac = server.getControlNICMac()
        logging.info(controlNICMac)

        datapathNICMac = server.getDatapathNICMac()
        logging.info(datapathNICMac)

        server.printCpuUtil()

if __name__=="__main__":
    logging.basicConfig(level=logging.DEBUG)
    controlIfName = "eno1"
    ServerTester(controlIfName)