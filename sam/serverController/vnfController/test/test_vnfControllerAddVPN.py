#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging
from scapy.all import *
import time

import pytest
from scapy.all import *

from sam.base import server
from sam.base.sfc import *
from sam.base.vnf import *
from sam.base.server import *
from sam.base.command import *
from sam.base.vpn import *
from sam.base.socketConverter import *
from sam.base.shellProcessor import ShellProcessor
from sam.test.fixtures.mediatorStub import *
from sam.test.fixtures.vnfControllerStub import *
from sam.test.testBase import *
from sam.serverController.classifierController import *

MANUAL_TEST = True
TESTER_SERVER_DATAPATH_IP = "2.2.0.36"
TESTER_SERVER_DATAPATH_MAC = "18:66:da:86:4c:16"
TESTER_DATAPATH_INTERFACE = "eno2"

SFF0_DATAPATH_IP = "2.2.0.38"
SFF0_DATAPATH_MAC = "00:1b:21:c0:8f:98"
SFF0_CONTROLNIC_IP = "192.168.0.173"
SFF0_CONTROLNIC_MAC = "18:66:da:85:1c:c3"

VPN_VNFI1_0_IP = "10.128.1.1"
VPN_VNFI1_1_IP = "10.128.1.128"

VPN_STARTPOINT_IP = "3.3.3.3"
VPN_ENDPOINT_IP = "4.4.4.4"

VPN_TunnelSrcIP = "3.3.3.3/32"
VPN_TunnelDstIP = "4.4.4.4"
VPN_EncryptKey = "11FF0183A9471ABE01FFFA04103BB102"
VPN_AuthKey = "11FF0183A9471ABE01FFFA04103BB202"

logging.basicConfig(level=logging.INFO)
logging.getLogger("pika").setLevel(logging.WARNING)

class TestVNFAddVPN(TestBase):
    @pytest.fixture(scope="function")
    def setup_addVPN(self):
        # setup
        self.sP = ShellProcessor()
        self.clearQueue()

        rabbitMQFilePath = server.__file__.split("server.py")[0] \
            + "rabbitMQConf.conf"
        logging.info(rabbitMQFilePath)
        self.resetRabbitMQConf(rabbitMQFilePath, "192.168.0.194",
            "mq", "123456")

        self.server = self.genTesterServer(TESTER_SERVER_DATAPATH_IP,
            TESTER_SERVER_DATAPATH_MAC)
        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genBiDirectionSFC(classifier, vnfTypeSeq=[VNF_TYPE_VPN])
        self.sfci = self.genBiDirection10BackupSFCI()
        self.mediator = MediatorStub()

        self.runSFFController()
        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.sfci)
        self.addSFCI2SFF()

        self.runVNFController()

        yield
        # teardown
        self.delVNFI4Server()   
        self.killSFFController()
        self.killVNFController()

    def gen10BackupVNFISequence(self, SFCLength=1):
        # hard-code function
        VNFISequence = []
        for index in range(SFCLength):
            VNFISequence.append([])
            for iN in range(1):
                server = Server("ens3", SFF0_DATAPATH_IP, SERVER_TYPE_NORMAL)
                server.setServerID(SERVERID_OFFSET + 1)
                server.setControlNICIP(SFF0_CONTROLNIC_IP)
                server.setControlNICMAC(SFF0_CONTROLNIC_MAC)
                server.setDataPathNICMAC(SFF0_DATAPATH_MAC)
                config = {}
                config['VPN'] = VPNTuple(VPN_TunnelSrcIP,VPN_TunnelDstIP, VPN_EncryptKey, VPN_AuthKey)
                vnfi = VNFI(VNF_TYPE_VPN, VNFType=VNF_TYPE_VPN, 
                    VNFIID=uuid.uuid1(), config=config, node=server)
                vnfi.maxCPUNum = 1
                VNFISequence[index].append(vnfi)
        return VNFISequence

    def addSFCI2SFF(self):
        logging.info("setup add SFCI to sff")
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SFF_CONTROLLER_QUEUE,
            MSG_TYPE_SSF_CONTROLLER_CMD , self.addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def delVNFI4Server(self):
        logging.warning("Deleting�VNFI")
        self.delSFCICmd = self.mediator.genCMDDelSFCI(self.sfc, self.sfci)
        self.sendCmd(VNF_CONTROLLER_QUEUE, MSG_TYPE_VNF_CONTROLLER_CMD,
            self.delSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def test_addVPN(self, setup_addVPN):
        # exercise
        logging.info("exercise")
        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.sfci)
        self.sendCmd(VNF_CONTROLLER_QUEUE,
            MSG_TYPE_VNF_CONTROLLER_CMD , self.addSFCICmd)

        # verifiy
        self.verifyCmdRply()
        self.verifyDirection0Traffic()
        # TODO: reverse direction - we need send back pkt in another thread
        # self.verifyDirection1Traffic()

    def verifyDirection0Traffic(self):
        self._sendDirection0Traffic2SFF()
        self._checkEncapsulatedTraffic(inIntf=TESTER_DATAPATH_INTERFACE)

    def _sendDirection0Traffic2SFF(self):
        filePath = "./fixtures/sendSFCTraffic.py -i " \
            + TESTER_DATAPATH_INTERFACE \
            + " -smac " + TESTER_SERVER_DATAPATH_MAC \
            + " -dmac " + SFF0_DATAPATH_MAC \
            + " -osip " + CLASSIFIER_DATAPATH_IP \
            + " -odip " + VPN_VNFI1_0_IP \
            + " -isip " + OUTTER_CLIENT_IP \
            + " -idip " + WEBSITE_REAL_IP \
            + " -pl HELLO_WORLD1234"
        self.sP.runPythonScript(filePath)

    def _checkEncapsulatedTraffic(self,inIntf):
        logging.info("_checkEncapsulatedTraffic: wait for packet")
        filterRE = "ether dst " + str(self.server.getDatapathNICMac())
        sniff(filter=filterRE,
            iface=inIntf, prn=self.encap_callback,count=1,store=0)

    def encap_callback(self,frame):
        frame.show()
        condition = (frame[IP].src == SFF0_DATAPATH_IP and \
            frame[IP].dst == SFCI1_0_EGRESS_IP and \
            frame[IP].proto == 0x04)
        assert condition
        outterPkt = frame.getlayer('IP')[0]
        innerPkt = frame.getlayer('IP')[1]
        assert innerPkt[IP].dst == VPN_ENDPOINT_IP and \
            innerPkt[IP].src == VPN_STARTPOINT_IP
        self.reverseTraffic = frame

    def verifyDirection1Traffic(self):
        self._sendDirection1Traffic2SFF()
        self._checkDecapsulatedTraffic(inIntf=TESTER_DATAPATH_INTERFACE)

    def _sendDirection1Traffic2SFF(self):
        self.reverseTraffic[Ether].src = TESTER_SERVER_DATAPATH_MAC
        self.reverseTraffic[Ether].dst = SFF0_DATAPATH_MAC
        outterPkt = self.reverseTraffic.getlayer('IP')[0]
        outterPkt[IP].src = CLASSIFIER_DATAPATH_IP
        outterPkt[IP].dst = VPN_VNFI1_1_IP
        innerPkt = self.reverseTraffic.getlayer('IP')[1]
        innerPkt[IP].src = VPN_ENDPOINT_IP
        innerPkt[IP].dst = VPN_STARTPOINT_IP
        self.reverseTraffic.show()
        sendp(self.reverseTraffic, iface=TESTER_DATAPATH_INTERFACE)

    def _checkDecapsulatedTraffic(self,inIntf):
        logging.info("_checkDecapsulatedTraffic: wait for packet")
        sniff(filter="ether dst " + str(self.server.getDatapathNICMac()),
            iface=inIntf, prn=self.decap_callback,count=1,store=0)

    def decap_callback(self,frame):
        frame.show()
        condition = (frame[IP].src == SFF0_DATAPATH_IP and \
            frame[IP].dst == SFCI1_1_EGRESS_IP and \
            frame[IP].proto == 0x04)
        assert condition == True
        outterPkt = frame.getlayer('IP')[0]
        innerPkt = frame.getlayer('IP')[1]
        assert innerPkt[IP].src == OUTTER_CLIENT_IP and \
            innerPkt[IP].dst == WEBSITE_REAL_IP

    def verifyCmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

