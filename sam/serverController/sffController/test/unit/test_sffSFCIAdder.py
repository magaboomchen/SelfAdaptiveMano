#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging
from scapy.all import *

import pytest

from sam.base.sfc import *
from sam.base.vnf import *
from sam.base.server import *
from sam.serverController.classifierController import *
from sam.base.command import *
from sam.base.socketConverter import *
from sam.base.shellProcessor import ShellProcessor
from sam.test.fixtures.mediatorStub import *
from sam.test.fixtures.vnfControllerStub import *
from sam.test.testBase import *

MANUAL_TEST = True

TESTER_SERVER_DATAPATH_IP = "192.168.124.1"
TESTER_SERVER_DATAPATH_MAC = "fe:54:00:42:26:44"

logging.basicConfig(level=logging.INFO)

class TestSFFSFCIAdderClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_addSFCI(self):
        # setup
        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genBiDirectionSFC(classifier)
        self.sfci = self.genBiDirection10BackupSFCI()
        self.mediator = MediatorStub()
        self.sP = ShellProcessor()
        self.sP.runShellCommand("sudo rabbitmqctl purge_queue MEDIATOR_QUEUE")
        self.sP.runShellCommand(
                "sudo rabbitmqctl purge_queue SFF_CONTROLLER_QUEUE")
        self.server = self.genTesterServer(TESTER_SERVER_DATAPATH_IP,
            TESTER_SERVER_DATAPATH_MAC)
        self.vC = VNFControllerStub()
        self.runSFFController()
        yield
        # teardown
        self.vC.uninstallVNF("t1", "123", "192.168.122.134",
            self.sfci.VNFISequence[0][0].VNFIID)
        self.killSFFController()

    def runSFFController(self):
        filePath = "~/HaoChen/Project/SelfAdaptiveMano/sam/serverController/sffController/sffControllerCommandAgent.py"
        self.sP.runPythonScript(filePath)

    def killSFFController(self):
        self.sP.killPythonScript("sffControllerCommandAgent.py")

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_addSFCI(self, setup_addSFCI):
        # exercise
        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.sfci)
        self.sendCmd(SFF_CONTROLLER_QUEUE,
            MSG_TYPE_SSF_CONTROLLER_CMD , self.addSFCICmd)

        # verify
        self.verifyArpResponder()
        self.verifyCmdRply()

        # setup again
        try:
            # In normal case, there should be a timeout error!
            shellCmdRply = self.vC.installVNF("t1", "123", "192.168.122.134",
                self.sfci.VNFISequence[0][0].VNFIID)
            logging.info(
                "command reply:\n stdin:{0}\n stdout:{1}\n stderr:{2}".format(
                None,
                shellCmdRply['stdout'].read().decode('utf-8'),
                shellCmdRply['stderr'].read().decode('utf-8')))
        except:
            logging.info("If raise IOError: reading from stdin while output is captured")
            logging.info("Then pytest should use -s option!")

        # verify again
        self.verifyDirection0Traffic()
        self.verifyDirection1Traffic()

    def verifyArpResponder(self):
        self._sendArpRequest(requestIP=SFF1_DATAPATH_IP)
        self._checkArpRespond(inIntf="toVNF1")

    def _sendArpRequest(self, requestIP):
        filePath = "~/HaoChen/Project/SelfAdaptiveMano/sam/serverController/sffController/test/unit/fixtures/sendArpRequest.py"
        self.sP.runPythonScript(filePath)

    def _checkArpRespond(self,inIntf):
        logging.info("_checkArpRespond: wait for packet")
        sniff(filter="ether dst " + str(self.server.getDatapathNICMac()) +
            " and arp",iface=inIntf, prn=self.frame_callback,count=1,store=0)

    def frame_callback(self,frame):
        frame.show()
        if frame[ARP].op == 2 and frame[ARP].psrc == SFF1_DATAPATH_IP:
            mac = frame[ARP].hwsrc
            assert mac.upper() == SFF1_DATAPATH_MAC


    def verifyDirection0Traffic(self):
        self._sendDirection0Traffic2SFF()
        self._checkEncapsulatedTraffic(inIntf="toVNF1")

    def _sendDirection0Traffic2SFF(self):
        filePath = "~/HaoChen/Project/SelfAdaptiveMano/sam/serverController/sffController/test/unit/fixtures/sendDirection0Traffic.py"
        self.sP.runPythonScript(filePath)

    def _checkEncapsulatedTraffic(self,inIntf):
        logging.info("_checkEncapsulatedTraffic: wait for packet")
        filterRE = "ether dst " + str(self.server.getDatapathNICMac())
        sniff(filter=filterRE,
            iface=inIntf, prn=self.encap_callback,count=1,store=0)

    def encap_callback(self,frame):
        frame.show()
        condition = (frame[IP].src == SFF1_DATAPATH_IP and \
            frame[IP].dst == SFCI1_0_EGRESS_IP and frame[IP].proto == 0x04)
        assert condition
        outterPkt = frame.getlayer('IP')[0]
        innerPkt = frame.getlayer('IP')[1]
        assert innerPkt[IP].dst == WEBSITE_REAL_IP


    def verifyDirection1Traffic(self):
        self._sendDirection1Traffic2SFF()
        self._checkDecapsulatedTraffic(inIntf="toVNF1")

    def _sendDirection1Traffic2SFF(self):
        filePath = "~/HaoChen/Project/SelfAdaptiveMano/sam/serverController/sffController/test/unit/fixtures/sendDirection1Traffic.py"
        self.sP.runPythonScript(filePath)

    def _checkDecapsulatedTraffic(self,inIntf):
        logging.info("_checkDecapsulatedTraffic: wait for packet")
        sniff(filter="ether dst " + str(self.server.getDatapathNICMac()),
            iface=inIntf, prn=self.decap_callback,count=1,store=0)

    def decap_callback(self,frame):
        frame.show()
        condition = (frame[IP].src == SFF1_DATAPATH_IP and \
            frame[IP].dst == SFCI1_1_EGRESS_IP and frame[IP].proto == 0x04)
        assert condition == True
        outterPkt = frame.getlayer('IP')[0]
        innerPkt = frame.getlayer('IP')[1]
        assert innerPkt[IP].src == WEBSITE_REAL_IP

    def verifyCmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

