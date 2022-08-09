#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
Usage:
    (1) sudo env "PATH=$PATH" python -m pytest ./test_sffPingEcho.py -s --disable-warnings
    (2) Please run 'python  ./serverAgent.py  0000:06:00.0  enp1s0  nfvi  2.2.0.98'
        on the NFVI running bess.
'''

import time

import pytest
from scapy.all import sniff
from scapy.layers.l2 import ARP, Ether
from scapy.layers.inet import IP, ICMP

from sam.base.compatibility import screenInput
from sam.base.command import CMD_STATE_SUCCESSFUL
from sam.base.messageAgent import SFF_CONTROLLER_QUEUE, MEDIATOR_QUEUE, \
    MSG_TYPE_SFF_CONTROLLER_CMD, TURBONET_ZONE, MessageAgent
from sam.base.shellProcessor import ShellProcessor
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.test.fixtures.vnfControllerStub import VNFControllerStub
from sam.test.testBase import TestBase, CLASSIFIER_DATAPATH_IP, \
    SFF1_DATAPATH_IP, SFF1_DATAPATH_MAC
from sam.test.fixtures import sendArpRequest, sendPing
from sam.serverController.sffController.test.component.testConfig import BESS_SERVER_DATAPATH_MAC, \
    TESTER_SERVER_DATAPATH_IP, TESTER_SERVER_DATAPATH_MAC, TESTER_DATAPATH_INTF
from sam.serverController.sffController import sffControllerCommandAgent


class TestSFFSFCIAdderClass(TestBase):
    @pytest.fixture(scope="function")

    def setup_addSFCI(self):
        logConfigur = LoggerConfigurator(__name__, './log',
            'tester.log', level='debug')
        self.logger = logConfigur.getLogger()
        self._messageAgent = MessageAgent(self.logger)

        # setup
        self.sP = ShellProcessor()
        self.clearQueue()
        self.killAllModule()

        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genBiDirectionSFC(classifier)
        self.sfci = self.genBiDirection10BackupSFCI()
        self.mediator = MediatorStub()

        self.server = self.genTesterServer(TESTER_SERVER_DATAPATH_IP,
                                            TESTER_SERVER_DATAPATH_MAC)
        self.vC = VNFControllerStub()
        self.runSFFController()

        yield

        # teardown
        self.killSFFController()

    def runSFFController(self):
        filePath = sffControllerCommandAgent.__file__
        self.sP.runPythonScript(filePath)

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_addSFCI(self, setup_addSFCI):
        # exercise
        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.sfci)
        queueName = self._messageAgent.genQueueName(SFF_CONTROLLER_QUEUE, TURBONET_ZONE)
        self.sendCmd(queueName, MSG_TYPE_SFF_CONTROLLER_CMD, self.addSFCICmd)

        # verify
        self.verifyCmdRply()
        time.sleep(2)
        self.logger.info("Press Any key to test data path!")
        screenInput()
        self.verifyArpResponder()
        self.verifyPingEcho()

    def verifyCmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        self.logger.info("Verify cmy rply successfully!")

    def verifyArpResponder(self):
        self._sendArpRequest(interface=TESTER_DATAPATH_INTF, requestIP=SFF1_DATAPATH_IP)
        self._checkArpRespond(inIntf=TESTER_DATAPATH_INTF)

    def _sendArpRequest(self, interface, requestIP, srcIP=TESTER_SERVER_DATAPATH_IP,
                        srcMAC=TESTER_SERVER_DATAPATH_MAC):
        filePath = sendArpRequest.__file__
        self.sP.runPythonScript(filePath \
            + " -i " + interface \
            + " -dip " + requestIP \
            + " -sip " + srcIP \
            + " -smac " + srcMAC)

    def _checkArpRespond(self,inIntf):
        self.logger.info("_checkArpRespond: wait for packet")
        sniff(filter="ether dst " + str(self.server.getDatapathNICMac()) +
            " and arp",iface=inIntf, prn=self.arpFrameCallback,count=1,store=0)
        self.logger.info("Check arp response successfully!")

    def arpFrameCallback(self,frame):
        frame.show()
        if frame[ARP].op == 2 and frame[ARP].psrc == SFF1_DATAPATH_IP:
            mac = frame[ARP].hwsrc
            assert mac.upper() == SFF1_DATAPATH_MAC.upper()





    def verifyPingEcho(self):
        self._sendPing(interface=TESTER_DATAPATH_INTF,
                        dstIP=SFF1_DATAPATH_IP)
        self._checkPingEchoRespond(inIntf=TESTER_DATAPATH_INTF)

    def _sendPing(self, interface, dstIP, srcIP=TESTER_SERVER_DATAPATH_IP,
                        srcMAC=TESTER_SERVER_DATAPATH_MAC,
                        dstMAC=BESS_SERVER_DATAPATH_MAC):
        filePath = sendPing.__file__
        self.sP.runPythonScript(filePath \
            + " -i " + interface \
            + " -dip " + dstIP \
            + " -sip " + srcIP \
            + " -smac " + srcMAC \
            + " -dmac " + dstMAC)

    def _checkPingEchoRespond(self, inIntf):
        self.logger.info("_checkPingEchoRespond: wait for packet")
        sniff(filter="ether dst " + str(self.server.getDatapathNICMac()) +
            " and icmp",iface=inIntf, prn=self.pingEchoFrameCallback,count=1,store=0)
        self.logger.info("Check ping echo successfully!")

    def pingEchoFrameCallback(self, frame):
        frame.show()
        mac = frame[Ether].src
        assert mac.upper() == BESS_SERVER_DATAPATH_MAC.upper()
        assert frame[IP].src == SFF1_DATAPATH_IP
        assert frame[IP].dst == TESTER_SERVER_DATAPATH_IP
        assert frame[ICMP].type == 0