from sam.base.sfc import *
from sam.base.vnf import *
from sam.base.server import *
from sam.serverController.classifierController import *
from sam.serverAgent.serverAgent import ServerAgent
from sam.base.command import *
from sam.base.socketConverter import *
from sam.base.shellProcessor import ShellProcessor
from sam.test.fixtures.mediatorStub import *
from sam.test.testBase import *
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

    @pytest.fixture(scope="function")
    def setup_orchestrationSendADDSFCI(self):
        # setup
        self.sp = ShellProcessor()
        self.sp.runPythonScript("~/HaoChen/Project/SelfAdaptiveMano/sam/serverController/classifierController/classifierControllerCommandAgent.py")
        yield
        # teardown
        self.sp.killPythonScript("classifierControllerCommandAgent.py")
        self.sp = None