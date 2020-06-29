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
sys.path.append("../")
from messageAgent import SAMMessage,MessageAgent
from server import Server
from serverManager import ServerManager

class ServerManagerTester():
    def __init__(self):
        self._test()

    def _test(self):
        SeverManager()

if __name__=="__main__":
    logging.basicConfig(level=logging.DEBUG)
    SeverManagerTester()