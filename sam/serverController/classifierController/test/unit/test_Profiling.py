#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging
from scapy.all import *

import pytest

from sam.base.sfc import *
from sam.base.vnf import *
from sam.base.server import *
from sam.base.command import *
from sam.base.socketConverter import SocketConverter, BCAST_MAC
from sam.base.shellProcessor import ShellProcessor
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.test.testBase import *
from sam.serverController.classifierController import ClassifierControllerCommandAgent
from sam.test.fixtures import sendArpRequest, sendInboundTraffic, sendOutSFCDomainTraffic

MANUAL_TEST = True

TESTER_SERVER_DATAPATH_IP = "2.2.0.33"
#TESTER_SERVER_DATAPATH_MAC = "f4:e9:d4:a3:53:a0"
#TESTER_SERVER_DATAPATH_MAC = "18:66:da:86:4c:16"
TESTER_SERVER_DATAPATH_MAC = "6c:b3:11:50:ec:64"

#TESTER_SERVER_INTERFACE = "eno2"
TESTER_SERVER_INTERFACE = "enp5s0f0"

CLASSIFIER_DATAPATH_MAC = "6c:b3:11:50:ec:3c"
#CLASSIFIER_DATAPATH_MAC = "00:1b:21:c0:8f:98"

CLASSIFIER_CONTROL_IP = "192.168.0.173"

WEBSITE_REAL_IP = "2.2.2.2"

logging.basicConfig(level=logging.INFO)
logging.getLogger("pika").setLevel(logging.WARNING)

# run scripts on dut 192.168.0.173
# python ./serverAgent.py 0000:04:00.0 eno1 classifier 2.2.0.36
# python ./serverAgent.py 0000:05:00.0 eno1 classifier 2.2.0.36


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
        self.server = self.genTesterServer(TESTER_SERVER_DATAPATH_IP,
            TESTER_SERVER_DATAPATH_MAC)
        self.runClassifierController()
        yield
        # teardown
        self.killClassifierController()

    def genClassifier(self, datapathIfIP):
        classifier = Server("ens3", datapathIfIP, SERVER_TYPE_CLASSIFIER)
        classifier.setServerID(CLASSIFIER_SERVERID)
        classifier._serverDatapathNICIP = CLASSIFIER_DATAPATH_IP
        classifier._ifSet["ens3"] = {}
        classifier._ifSet["ens3"]["IP"] = CLASSIFIER_CONTROL_IP
        classifier._serverDatapathNICMAC = CLASSIFIER_DATAPATH_MAC
        return classifier

    def genBiDirectionSFC(self, classifier, vnfTypeSeq=[VNF_TYPE_FORWARD]):
        sfcUUID = uuid.uuid1()
        vNFTypeSequence = vnfTypeSeq
        maxScalingInstanceNumber = 1
        backupInstanceNumber = 0
        applicationType = APP_TYPE_NORTHSOUTH_WEBSITE
        direction1 = {
            'ID': 0,
            'source': {"IPv4":"*"},
            'ingress': classifier,
            'match': {'srcIP': "*",'dstIP':WEBSITE_REAL_IP,
                'srcPort': "*",'dstPort': "*",'proto': "*"},
            'egress': classifier,
            'destination': {"IPv4":WEBSITE_REAL_IP}
        }
        direction2 = {
            'ID': 1,
            'source': {"IPv4":WEBSITE_REAL_IP},
            'ingress': classifier,
            'match': {'srcIP': WEBSITE_REAL_IP,'dstIP': "*",
                'srcPort': "*",'dstPort': "*",'proto': "*"},
            'egress': classifier,
            'destination': "*"
        }
        directions = [direction1,direction2]
        return SFC(sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
            backupInstanceNumber, applicationType, directions, {'zone':""})

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
        logging.info("please start performance profiling" \
            "after profiling, press any key to quit.")
        raw_input()

    def verifyArpResponder(self):
        self._sendArpRequest(requestIP=CLASSIFIER_DATAPATH_IP)
        self._checkArpRespond(inIntf=TESTER_SERVER_INTERFACE)

    def _sendArpRequest(self, requestIP):
        filePath = sendArpRequest.__file__
        self.sP.runPythonScript(filePath \
            + " -i " + TESTER_SERVER_INTERFACE + " -sip "\
            + TESTER_SERVER_DATAPATH_IP + " -dip " \
            + requestIP + " -smac " + TESTER_SERVER_DATAPATH_MAC)

    def _checkArpRespond(self,inIntf):
        logging.info("_checkArpRespond: wait for packet")
        sniff(filter="ether dst " + str(self.server.getDatapathNICMac()) +
            " and arp",iface=inIntf, prn=self.frame_callback,count=1, store=0)

    def frame_callback(self,frame):
        frame.show()
        if frame[ARP].op == 2 and frame[ARP].psrc == CLASSIFIER_DATAPATH_IP:
            mac = frame[ARP].hwsrc
            assert mac.upper() == CLASSIFIER_DATAPATH_MAC.upper()

    def verifyInboundTraffic(self):
        self._sendInboundTraffic2Classifier()
        self._checkEncapsulatedTraffic(inIntf=TESTER_SERVER_INTERFACE)

    def _sendInboundTraffic2Classifier(self):
        filePath = sendInboundTraffic.__file__
        self.sP.runPythonScript(filePath \
            + " -i " + TESTER_SERVER_INTERFACE + " -smac " \
            + TESTER_SERVER_DATAPATH_MAC \
            + " -dmac " + CLASSIFIER_DATAPATH_MAC + " -sip " \
            + OUTTER_CLIENT_IP + " -dip " + WEBSITE_REAL_IP
            )

    def _checkEncapsulatedTraffic(self,inIntf):
        logging.info("_checkEncapsulatedTraffic: wait for packet")
        filterRE = "ether dst " + str(self.server.getDatapathNICMac())
        sniff(filter=filterRE,
            iface=inIntf, prn=self.encap_callback,count=1, store=0)

    def encap_callback(self,frame):
        frame.show()
        condition = (frame[IP].src == CLASSIFIER_DATAPATH_IP \
            and frame[IP].dst == VNFI1_0_IP and frame[IP].proto == 0x04)
        assert condition
        outterPkt = frame.getlayer('IP')[0]
        # outterPkt.show()
        innerPkt = frame.getlayer('IP')[1]
        # innerPkt.show()
        assert innerPkt[IP].dst == WEBSITE_REAL_IP

    def verifyOutSFCDomainTraffic(self):
        self._sendOutSFCDomainTraffic2Classifier()
        self._checkDecapsulatedTraffic(inIntf=TESTER_SERVER_INTERFACE)

    def _sendOutSFCDomainTraffic2Classifier(self):
        filePath = sendOutSFCDomainTraffic.__file__
        self.sP.runPythonScript(filePath + " -i " + TESTER_SERVER_INTERFACE \
            + " -smac " + TESTER_SERVER_DATAPATH_MAC \
            + " -dmac " + CLASSIFIER_DATAPATH_MAC \
            + " -osip " + VNFI1_0_IP + " -odip " + SFCI1_0_EGRESS_IP \
            + " -isip " + WEBSITE_REAL_IP + " -idip " + OUTTER_CLIENT_IP
        )

    def _checkDecapsulatedTraffic(self,inIntf):
        logging.info("_checkDecapsulatedTraffic: wait for packet")
        sniff(filter="ether dst " + str(self.server.getDatapathNICMac()),
            iface=inIntf, prn=self.decap_callback,count=1, store=0)

    def decap_callback(self,frame):
        frame.show()
        condition = (frame[IP].src == WEBSITE_REAL_IP \
            and frame[IP].dst == OUTTER_CLIENT_IP)
        assert condition == True

    def verifyCmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL