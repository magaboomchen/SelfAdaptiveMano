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
sys.path.append("../")
from argParser import ArgParser
from systemChecker import SystemChecker
from dpdkConfigure import DPDKConfigurator
from messageAgent import *
from bessStarter import BessStarter
from serverAgent import ServerAgent
from server import Server

class ServerTester():
    def __init__(self,controlIfName):
        server = Server(controlIfName)

        server.updateIfSet()

        ifset = server.getIfSet()
        logging.info(ifset)

        server.printIfSet()

        controlNICMac = server.getControlNICMac()
        logging.info(controlNICMac)

        datapathNICMac = server.getDatapathNICMac()
        logging.info(datapathNICMac)

if __name__=="__main__":
    logging.basicConfig(level=logging.DEBUG)
    controlIfName = "ens3"
    ServerTester(controlIfName)