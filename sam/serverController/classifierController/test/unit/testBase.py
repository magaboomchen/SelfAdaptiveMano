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

class TestBase(object):
    def setup_method(self, method):
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """
        self.oS = OrchestrationStub()
        self.server = Server("virbr0", "192.168.123.1", SERVER_TYPE_TESTER)
        self.server.updateServerID(uuid.uuid1())
        self.server.updateControlNICMAC()
        self.server.updateIfSet()
        self.server._serverDatapathNICMAC = "fe:54:00:05:4d:7d"
        self.sp = ShellProcessor()
        self.sp.runPythonScript("~/HaoChen/Project/SelfAdaptiveMano/sam/serverController/classifierController/classifierControllerCommandAgent.py")
        self.classifier = None
        self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = None
        self.genSFC4test()

    def teardown_method(self, method):
        """ teardown any state that was previously setup with a setup_method
        call.
        """
        self.oS = None
        self.sfc = None
        self.server = None
        self.classifier = None
        self.sp.killPythonScript("classifierControllerCommandAgent.py")
        self.sp = None

    def genClassifier(self, datapathIfIP):
        self.classifier = Server("ens3", datapathIfIP, SERVER_TYPE_CLASSIFIER)
        self.classifier.updateServerID(uuid.uuid1())
        self.classifier._ifSet["ens3"] = {}
        self.classifier._ifSet["ens3"]["IP"] = CLASSIFIER_CONTROL_IP
        self.classifier._serverDatapathNICMAC = CLASSIFIER_DATAPATH_MAC

    def genSFC4test(self):
        sfcUUID = uuid.uuid1()
        vNFTypeSequence = [VNF_TYPE_FW]
        maxScalingInstanceNumber = 1
        backupInstanceNumber = 0
        applicationType = APP_TYPE_NORTHSOUTH_WEBSITE
        direction1 = {
            'ID': 0,
            'source': None,
            'ingress': self.classifier,
            'match': {'srcIP': None,'dstIP':WEBSITE_VIRTUAL_IP,
                'srcPort': None,'dstPort': None,'proto': None},
            'egress': self.classifier,
            'destination': WEBSITE_REAL_IP
        }
        direction2 = {
            'ID': 1,
            'source': WEBSITE_VIRTUAL_IP,
            'ingress': self.classifier,
            'match': {'srcIP': WEBSITE_VIRTUAL_IP,'dstIP':None,
                'srcPort': None,'dstPort': None,'proto': None},
            'egress': self.classifier,
            'destination': None
        }
        directions = [direction1,direction2]
        self.sfc = SFC(sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
            backupInstanceNumber, applicationType, directions)