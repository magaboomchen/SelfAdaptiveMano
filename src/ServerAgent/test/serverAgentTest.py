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

HEAT_BEAT_TIME = 10

class ServerAgentTester():
    def __init__(self,controlNICName):
        serverAgent = ServerAgent(controlNICName)
        serverAgent.run()

if __name__=="__main__":
    logging.basicConfig(level=logging.DEBUG)
    ControllNICName = "ens3"
    ServerAgentTester(ControllNICName)