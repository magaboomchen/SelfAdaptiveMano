import pytest
from scapy.all import *

from sam.base.sfc import *
from sam.base.vnf import *
from sam.base.server import *
from sam.serverController.classifierController import *
from sam.base.command import *
from sam.base.socketConverter import *
from sam.base.shellProcessor import ShellProcessor
from sam.test.fixtures.mediatorStub import *
from sam.test.testBase import *

MANUAL_TEST = True

TESTER_SERVER_DATAPATH_IP = "192.168.123.1"
TESTER_SERVER_DATAPATH_MAC = "fe:54:00:05:4d:7d"

class TestSFCIAdderClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_addSFCI(self):
        # setup
        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genBiDirectionSFC(classifier)
        self.sfci = self.genBiDirection10BackupSFCI()
        self.mediator = MediatorStub()
        self.sP = ShellProcessor()
        self.sP.runShellCommand("sudo rabbitmqctl purge_queue MEDIATOR_QUEUE")
        self.sP.runShellCommand("sudo rabbitmqctl purge_queue SERVER_CLASSIFIER_CONTROLLER_QUEUE")
        self.server = self.genTesterServer("192.168.123.1","fe:54:00:05:4d:7d")
        self.runClassifierController()
        yield
        # teardown
        self.killClassifierController()

    def runClassifierController(self):
        filePath = "~/HaoChen/Project/SelfAdaptiveMano/sam/serverController/classifierController/classifierControllerCommandAgent.py"
        self.sP.runPythonScript(filePath)

    def killClassifierController(self):
        self.sP.killPythonScript("classifierControllerCommandAgent.py")

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_addSFCI(self, setup_addSFCI):
        # exercise
        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.sfci)
        self.sendCmd(SERVER_CLASSIFIER_CONTROLLER_QUEUE,
            MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, self.addSFCICmd)
        # verify
        self.verifyArpResponder()
        self.verifyInboundTraffic()
        self.verifyOutSFCDomainTraffic()
        self.verifyCmdRply()

    def verifyArpResponder(self):
        self._sendArpRequest(requestIP=CLASSIFIER_DATAPATH_IP)
        self._checkArpRespond(inIntf="toClassifier")

    def _sendArpRequest(self, requestIP):
        filePath = "~/HaoChen/Project/SelfAdaptiveMano/sam/serverController/classifierController/test/unit/fixtures/sendArpRequest.py"
        self.sP.runPythonScript(filePath)

    def _checkArpRespond(self,inIntf):
        print("_checkArpRespond: wait for packet")
        sniff(filter="ether dst " + str(self.server.getDatapathNICMac()) +
            " and arp",iface=inIntf, prn=self.frame_callback,count=1,store=0)

    def frame_callback(self,frame):
        frame.show()
        if frame[ARP].op == 2 and frame[ARP].psrc == CLASSIFIER_DATAPATH_IP:
            mac = frame[ARP].hwsrc
            assert mac.upper() == CLASSIFIER_DATAPATH_MAC

    def verifyInboundTraffic(self):
        self._sendInboundTraffic2Classifier()
        self._checkEncapsulatedTraffic(inIntf="toClassifier")

    def _sendInboundTraffic2Classifier(self):
        filePath = "~/HaoChen/Project/SelfAdaptiveMano/sam/serverController/classifierController/test/unit/fixtures/sendInboundTraffic.py"
        self.sP.runPythonScript(filePath)

    def _checkEncapsulatedTraffic(self,inIntf):
        print("_checkEncapsulatedTraffic: wait for packet")
        filterRE = "ether dst " + str(self.server.getDatapathNICMac())
        sniff(filter=filterRE,
            iface=inIntf, prn=self.encap_callback,count=1,store=0)

    def encap_callback(self,frame):
        frame.show()
        condition = (frame[IP].src == CLASSIFIER_DATAPATH_IP and frame[IP].dst == VNFI1_0_IP and frame[IP].proto == 0x04)
        assert condition
        outterPkt = frame.getlayer('IP')[0]
        # outterPkt.show()
        innerPkt = frame.getlayer('IP')[1]
        # innerPkt.show()
        assert innerPkt[IP].dst == WEBSITE_REAL_IP

    def verifyOutSFCDomainTraffic(self):
        self._sendOutSFCDomainTraffic2Classifier()
        self._checkDecapsulatedTraffic(inIntf="toClassifier")

    def _sendOutSFCDomainTraffic2Classifier(self):
        filePath = "~/HaoChen/Project/SelfAdaptiveMano/sam/serverController/classifierController/test/unit/fixtures/sendOutSFCDomainTraffic.py"
        self.sP.runPythonScript(filePath)

    def _checkDecapsulatedTraffic(self,inIntf):
        print("_checkDecapsulatedTraffic: wait for packet")
        sniff(filter="ether dst " + str(self.server.getDatapathNICMac()),
            iface=inIntf, prn=self.decap_callback,count=1,store=0)

    def decap_callback(self,frame):
        frame.show()
        condition = (frame[IP].src == WEBSITE_REAL_IP and frame[IP].dst == OUTTER_CLIENT_IP)
        assert condition == True

    def verifyCmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL