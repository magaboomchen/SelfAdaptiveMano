from sam.base.sfc import *
from sam.base.vnf import *
from sam.base.server import *
from sam.serverController.classifierController import *
from sam.serverAgent.serverAgent import ServerAgent
from sam.base.command import *
from sam.base.socketConverter import *
from sam.base.shellProcessor import ShellProcessor
from sam.serverController.classifierController.test.unit.fixtures.orchestrationStub import *
from sam.serverController.classifierController.test.unit.testBase import *
import uuid
import subprocess
import psutil
import pytest
import time
from scapy.all import *

MANUAL_TEST = True

class TestClassifierControllerCommandAgentClass(TestBase):
    # use mock to test whether methods has been called
    pass