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

class TestSFCinitializerClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_addSFCI(self):
        # setup
        self.sfci = self.genSFCI()
        self.sfc.sFCIs[self.sfci.SFCIID] = self.sfci
        self.oS.sendCMDInitClassifier(self.sfc)
        yield
        # teardown
        pass

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_initClassifier(self):
        # exercise
        self.oS.sendCMDInitClassifier(self.sfc)
        # verify
        time.sleep(2)
        self.verifyArpResponder()

    def genSFCI(self):
        VNFISequence = self.genVNFISequence()
        return SFCI(uuid.uuid1(),VNFISequence)

    def genVNFISequence(self,SFCLength=1):
        VNFISequence = []
        for index in range(SFCLength):
            server = Server("ens3",VNFI1_IP,SERVER_TYPE_NORMAL)
            vnfi = VNFI(uuid.uuid1(),VNFType=VNF_TYPE_FW,VNFIID=VNF_TYPE_FW,
                server=server)
            VNFISequence.append(vnfi)
        return VNFISequence

    def verifyArpResponder(self):
        self._sendArpRequest(outIntf="toClassifier", requestIP=CLASSIFIER_DATAPATH_IP)
        self._checkArpRespond(inIntf="toClassifier")

    def _sendArpRequest(self, outIntf, requestIP):
        filePath = "~/HaoChen/Project/SelfAdaptiveMano/sam/serverController/classifierController/test/unit/fixtures/sendArpRequest.py"
        self.sp.runPythonScript(filePath)

    def _checkArpRespond(self,inIntf):
        print("_checkArpRespond: wait for packet")
        sniff(filter="ether dst " + str(self.server.getDatapathNICMac()) +
            " and arp",iface=inIntf, prn=self.frame_callback,count=1,store=0)

    def frame_callback(self,frame):
        frame.show()
        if frame[ARP].op == 2 and frame[ARP].psrc == CLASSIFIER_DATAPATH_IP:
            mac = frame[ARP].hwsrc
            assert mac.upper() == CLASSIFIER_DATAPATH_MAC
