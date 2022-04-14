#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging
from scapy.all import *

import pytest

from sam.base.sfc import *
from sam.base.vnf import *
from sam.base.server import *
from sam.serverController.classifierController import ClassifierControllerCommandAgent
from sam.base.command import *
from sam.base.socketConverter import SocketConverter, BCAST_MAC
from sam.base.shellProcessor import ShellProcessor
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.test.testBase import *
from sam.test.fixtures import sendArpRequest, sendInboundTraffic, sendOutSFCDomainTraffic

MANUAL_TEST = True

TESTER_SERVER_DATAPATH_IP = "192.168.123.1"
TESTER_SERVER_DATAPATH_MAC = "fe:54:00:05:4d:7d"

logging.basicConfig(level=logging.INFO)
logging.getLogger("pika").setLevel(logging.WARNING)

class TestSFCIAdderClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_addSFCI(self):
        # setup
        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genBiDirectionSFC(classifier)
        self.sfci = self.genBiDirection10BackupSFCI()
        self.mediator = MediatorStub()
        self.sP = ShellProcessor()
        self.clearQueue()
        self.server = self.genTesterServer(TESTER_SERVER_DATAPATH_IP, TESTER_SERVER_DATAPATH_MAC)
        self.runClassifierController()
        yield
        # teardown
        self.killClassifierController()

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_addSFCI(self, setup_addSFCI):
        # exercise
        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.sfci)
        self.sendCmd(SERVER_CLASSIFIER_CONTROLLER_QUEUE,
            MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, self.addSFCICmd)
        # verify
        self.verifyCmdRply()
        self.verifyArpResponder()
        self.verifyInboundTraffic()
        self.verifyOutSFCDomainTraffic()

    def verifyArpResponder(self):
        self._sendArpRequest(requestIP=CLASSIFIER_DATAPATH_IP)
        self._checkArpRespond(inIntf="toClassifier")

    def _sendArpRequest(self, requestIP):
        filePath = sendArpRequest.__file__
        self.sP.runPythonScript(filePath + " -dip " + requestIP)

    def _checkArpRespond(self,inIntf):
        logging.info("_checkArpRespond: wait for packet")
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
        filePath = sendInboundTraffic.__file__
        self.sP.runPythonScript(filePath)

    def _checkEncapsulatedTraffic(self,inIntf):
        logging.info("_checkEncapsulatedTraffic: wait for packet")
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
        filePath = sendOutSFCDomainTraffic.__file__
        self.sP.runPythonScript(filePath)

    def _checkDecapsulatedTraffic(self,inIntf):
        logging.info("_checkDecapsulatedTraffic: wait for packet")
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