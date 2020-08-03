from sam.base.sfc import *
from sam.base.vnf import *
from sam.base.server import *
from sam.serverController.classifierController import *
from sam.serverAgent.serverAgent import ServerAgent
from sam.base.command import *
from sam.base.socketConverter import *
from sam.base.shellProcessor import ShellProcessor
from sam.serverController.classifierController.test.unit.fixtures.orchestrationStub import *
import uuid
import subprocess
import psutil
import pytest
import time
from scapy.all import *
from sam.serverController.classifierController.classifierIBMaintainer import *
from sam.serverController.classifierController.test.unit.testBase import *

MANUAL_TEST = True

class TestClassifierIBMaintainerClass(TestBase):
    def setup_method(self, method):
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """
        self.cM = ClassifierIBMaintainer()
        self.classifier = None
        self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = None
        self.genSFC4test()

    def teardown_method(self, method):
        """ teardown any state that was previously setup with a setup_method
        call.
        """
        self.cM = None
        self.classifier = None

    def test_initClassifier(self):
        ingress = self.classifier
        serverID = ingress.getServerID()
        self.cM.initClassifier(ingress)
        assert serverID in self.cM.classifiers.iterkeys()
        assert self.cM.classifiers[serverID].server == ingress

    def test_isClassifierInit(self):
        ingress = self.classifier
        serverID = ingress.getServerID()
        assert self.cM.isClassifierInit(ingress) == False
        self.cM.classifiers[serverID] = ingress
        assert self.cM.isClassifierInit(ingress) == True

    @pytest.fixture(scope="function")
    def setup_initClassifier(self):
        # setup
        ingress = self.classifier
        serverID = ingress.getServerID()
        self.cM.initClassifier(ingress)
        yield
        # teardown

    def test_addSFC2Classifier(self, setup_initClassifier):
        ingress = self.classifier
        serverID = ingress.getServerID()
        sfc = self.sfc
        sfcUUID = sfc.sfcUUID
        direction = 0
        hashLBName = "hashLB_" + str(sfcUUID) + '_' + str(direction)
        self.cM.addSFC2Classifier(ingress,sfc,2,hashLBName)
        assert hashLBName in self.cM.classifiers[serverID].wm2Gate.iterkeys() == True
        assert hashLBName in self.cM.classifiers[serverID].hlbGate.iterkeys() == True


