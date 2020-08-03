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

class TestSFCIAdderClass(TestBase):
    @pytest.mark.skip(reason='Skip temporarily')
    def test_addSFCI(self, setup_addSFCI):
        # exercise
        self.oS.sendCMDAddSFC(self.sfc)
        self.oS.sendCMDAddSFCI(self.sfc, self.sfci)
        # verify
        self.verifyInboundTraffic()
        self.verifyOutSFCDomainTraffic()
        TODO: bi-direction test

    def verifyInboundTraffic(self):
        self._sendInboundTraffic2Classifier()
        self._checkEncapsulatedTraffic(inIntf="toClassifier")

    def _sendInboundTraffic2Classifier(self):
        filePath = "~/HaoChen/Project/SelfAdaptiveMano/sam/serverController/classifierController/test/unit/fixtures/sendInboundTraffic.py"
        self.sp.runPythonScript(filePath)

    def _checkEncapsulatedTraffic(self,inIntf):
        print("_checkEncapsulatedTraffic: wait for packet")
        sniff(filter="ether dst " + str(self.server.getDatapathNICMac()),
            iface=inIntf, prn=self.encap_callback,count=1,store=0)

    def encap_callback(self,frame):
        frame.show()
        frame[IP].summary()
        condition = (frame[IP].src == CLASSIFIER_DATAPATH_IP and frame[IP].dst == VNFI1_IP and frame[IP].proto == 0x04)
        assert condition == True
        print(frame.getlayer('IP'))
        # TODO: check the usage of scapy
        innerPkt = frame.getlayer('IP')[1]
        assert innerPkt[IP].dst == WEBSITE_VIRTUAL_IP

    def verifyOutSFCDomainTraffic(self):
        self._sendOutSFCDomainTraffic2Classifier()
        self._checkDecapsulatedTraffic()

    def _sendOutSFCDomainTraffic2Classifier(self):
        filePath = "~/HaoChen/Project/SelfAdaptiveMano/sam/serverController/classifierController/test/unit/fixtures/sendOutSFCDomainTraffic.py"
        self.sp.runPythonScript(filePath)
    
    def _checkDecapsulatedTraffic(self):
        print("_checkDecapsulatedTraffic: wait for packet")
        sniff(filter="ether dst " + str(self.server.getDatapathNICMac()),
            iface=inIntf, prn=self.decap_callback,count=1,store=0)

    def decap_callback(self,frame):
        frame.show()
        condition = (frame[IP].src == VNFI1_IP and frame[IP].dst == WEBSITE_VIRTUAL_IP)
        assert condition == True
    @pytest.fixture(scope="function")
    def setup_cC(self):
        # setup
        self.cC = ClassifierController()
        self.serverID = uuid.uuid1()
        self.sfcUUID = uuid.uuid1()
        self.cC._classifierSet[self.serverID] = {"server":None,"sfcSet":{}}
        self.cC._classifierSet[self.serverID]["sfcSet"][self.sfcUUID] = {}
        yield
        # teardown
        self.cC = None

    def test_getwm2Rule(self, setup_cC):
        [values,masks] = self.cC._getwm2Rule(self.sfc.directions[0]['match'])
        assert values == [
            {'value_bin': '\x00'},
            {'value_bin': '\x00\x00\x00\x00\x00\x00\x00\x00'},
            {'value_bin': '\x02\x02\x02\x02'},
            {'value_bin': '\x00\x00'},
            {'value_bin': '\x00\x00'}
        ]
        assert masks == [
            {'value_bin': '\x00'},
            {'value_bin': '\x00\x00\x00\x00\x00\x00\x00\x00'},
            {'value_bin': '\xff\xff\xff\xff\xff\xff\xff\xff'},
            {'value_bin': '\x00\x00'},
            {'value_bin': '\x00\x00'}
        ]

    @pytest.mark.skip(reason='Skip temporarily')
    def test_genwm2GateNum(self, setup_cC):
        num = self.cC._genwm2GateNum(self.serverID, self.sfcUUID)
        assert num == 2

    @pytest.mark.skip(reason='Skip temporarily')
    def test_getewm2GateNum(self, setup_cC):
        num = self.cC._genwm2GateNum(self.serverID, self.sfcUUID)
        assert self.cC._getewm2GateNum(self.serverID, self.sfcUUID) == num