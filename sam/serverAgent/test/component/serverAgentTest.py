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
import threading
from sam.base.messageAgent import *
from sam.serverAgent.serverAgent import ServerAgent
from sam.base.server import Server
# TODO: refactor, pytest
class ServerAgentTester(object):
    def __init__(self,controlNICName):
        serverAgent = ServerAgent(controlNICName)
        serverAgent.run()

if __name__=="__main__":
    logging.basicConfig(level=logging.DEBUG)
    ControllNICName = "ens3"
    ServerAgentTester(ControllNICName)