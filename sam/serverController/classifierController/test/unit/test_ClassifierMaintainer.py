from sam.base.sfc import *
from sam.base.vnf import *
from sam.base.server import *
from sam.serverController.classifierController import *
from sam.serverAgent.serverAgent import ServerAgent
from sam.base.command import *
from sam.base.socketConverter import *
from sam.base.shellProcessor import ShellProcessor
from sam.test.fixtures.mediatorStub import *
import uuid
import subprocess
import psutil
import pytest
import time
from scapy.all import *
from sam.serverController.classifierController.classifierIBMaintainer import *
from sam.test.testBase import *

MANUAL_TEST = True

# TODO need refactor

class TestClassifierIBMaintainerClass(TestBase):
    def setup_method(self, method):
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """
        self.cM = ClassifierIBMaintainer()

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


