#!/usr/bin/python
# -*- coding: UTF-8 -*-

raise ValueError("Haven't refactor!")

import time
import logging

import pytest
from scapy.all import sniff
from scapy.layers.l2 import  ARP
from scapy.layers.inet import IP

from sam.base.command import CMD_STATE_SUCCESSFUL
from sam.base.messageAgent import SFF_CONTROLLER_QUEUE, MEDIATOR_QUEUE, \
    MSG_TYPE_SFF_CONTROLLER_CMD
from sam.base.shellProcessor import ShellProcessor
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.test.fixtures.vnfControllerStub import VNFControllerStub
from sam.test.testBase import TestBase, CLASSIFIER_DATAPATH_IP, SFF1_DATAPATH_IP, \
    SFF1_DATAPATH_MAC, SFCI1_0_EGRESS_IP, WEBSITE_REAL_IP, SFCI1_1_EGRESS_IP
from sam.test.fixtures import sendArpRequest
from sam.serverController.sffController.test.unit.fixtures import sendDirection0Traffic
from sam.serverController.sffController.test.unit.fixtures import sendDirection0Traffic4sfci2
from sam.serverController.sffController.test.unit.fixtures import sendDirection1Traffic
from sam.serverController.sffController.test.unit.fixtures import sendDirection1Traffic4sfci2

MANUAL_TEST = True

TESTER_SERVER_DATAPATH_IP = "192.168.8.20"
TESTER_SERVER_DATAPATH_MAC = "90:e2:ba:b1:4d:0f"

SFCI2_0_EGRESS_IP = "10.0.2.1"
SFCI2_1_EGRESS_IP = "10.0.2.128"

logging.basicConfig(level=logging.INFO)


class TestSFFSFCIAdderReassignVNFIClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_addTwoSFCIs(self):
        # setup
        self.sP = ShellProcessor()
        self.clearQueue()
        self.killAllModule()

        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc1 = self.genBiDirectionSFC(classifier)
        self.sfci1 = self.genBiDirection10BackupSFCI()
        self.sfc2 = self.genBiDirectionSFC(classifier)
        self.sfci2 = self.genBiDirection10BackupSFCI()
        self._reassignVNFI2SFCI()

        self.mediator = MediatorStub()

        self.server = self.genTesterServer(TESTER_SERVER_DATAPATH_IP,
                                            TESTER_SERVER_DATAPATH_MAC)
        self.vC = VNFControllerStub()
        self.runSFFController()

        yield

        # teardown
        self.vC.uninstallVNF("t1", "123", "192.168.122.134",
            self.sfci1.vnfiSequence[0][0].vnfiID)
        self.killSFFController()

    def _reassignVNFI2SFCI(self):
        vnfiID = self.sfci1.vnfiSequence[0][0].vnfiID
        self.sfci2.vnfiSequence[0][0].vnfiID = vnfiID

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_addSFCIReassignVNFI(self, setup_addTwoSFCIs):
        # exercise
        self.addSFCI1Cmd = self.mediator.genCMDAddSFCI(self.sfc1, self.sfci1)
        self.sendCmd(SFF_CONTROLLER_QUEUE,
                    MSG_TYPE_SFF_CONTROLLER_CMD,
                    self.addSFCI1Cmd)
        self.addSFCI2Cmd = self.mediator.genCMDAddSFCI(self.sfc2, self.sfci2)
        self.sendCmd(SFF_CONTROLLER_QUEUE,
                    MSG_TYPE_SFF_CONTROLLER_CMD,
                    self.addSFCI2Cmd)

        # verify
        self.verifyCmdRply()
        self.verifyArpResponder()

        # setup again
        try:
            # In normal case, there should be a timeout error!
            shellCmdRply = self.vC.installVNF("t1", "123", "192.168.122.134",
                self.sfci1.vnfiSequence[0][0].vnfiID)
            logging.info(
                "command reply:\n stdin:{0}\n stdout:{1}\n stderr:{2}".format(
                None,
                shellCmdRply['stdout'].read().decode('utf-8'),
                shellCmdRply['stderr'].read().decode('utf-8')))
        except:
            logging.info("If raise IOError: reading from stdin while output is captured")
            logging.info("Then pytest should use -s option!")

        # verify again
        time.sleep(5)
        self.verifyDirection0Traffic()
        self.verifyDirection1Traffic()

    def verifyCmdRply(self):
        # verify cmd1
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCI1Cmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        # verify cmd2
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCI2Cmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def verifyArpResponder(self):
        self._sendArpRequest(interface=TESTER_SERVER_INTF, requestIP=SFF1_DATAPATH_IP)
        self._checkArpRespond(inIntf=TESTER_SERVER_INTF)

    def _sendArpRequest(self, interface, requestIP):
        filePath = sendArpRequest.__file__
        self.sP.runPythonScript(filePath \
            + " -i " + interface \
            + " -dip " + requestIP)

    def _checkArpRespond(self,inIntf):
        logging.info("_checkArpRespond: wait for packet")
        sniff(
            filter="ether dst " + str(self.server.getDatapathNICMac()) +
            " and arp",iface=inIntf, prn=self.frame_callback,count=1,store=0)

    def frame_callback(self,frame):
        frame.show()
        if frame[ARP].op == 2 and frame[ARP].psrc == SFF1_DATAPATH_IP:
            mac = frame[ARP].hwsrc
            assert mac.upper() == SFF1_DATAPATH_MAC.upper()


    def verifyDirection0Traffic(self):
        self._sendDirection0Traffic2SFF()
        self._checkEncapsulatedTraffic(inIntf=TESTER_SERVER_INTF)

        self._sendDirection0Traffic2SFF4sfci2()
        self._checkEncapsulatedTraffic4sfci2(inIntf=TESTER_SERVER_INTF)

    def _sendDirection0Traffic2SFF(self):
        filePath = sendDirection0Traffic.__file__
        self.sP.runPythonScript(filePath)

    def _checkEncapsulatedTraffic(self, inIntf):
        logging.info("_checkEncapsulatedTraffic: wait for packet")
        filterRE = "ether dst " + str(self.server.getDatapathNICMac())
        sniff(
            filter=filterRE,
            iface=inIntf, prn=self.encap_callback,count=1, store=0)

    def encap_callback(self,frame):
        frame.show()
        condition = (frame[IP].src == SFF1_DATAPATH_IP 
                        and frame[IP].dst == SFCI1_0_EGRESS_IP
                        and frame[IP].proto == 0x04)
        assert condition
        outterPkt = frame.getlayer('IP')[0]
        innerPkt = frame.getlayer('IP')[1]
        assert innerPkt[IP].dst == WEBSITE_REAL_IP

    def _sendDirection0Traffic2SFF4sfci2(self):
        filePath = sendDirection0Traffic4sfci2.__file__
        self.sP.runPythonScript(filePath)

    def _checkEncapsulatedTraffic4sfci2(self, inIntf):
        logging.info("_checkEncapsulatedTraffic for sfci2: wait for packet")
        filterRE = "ether dst " + str(self.server.getDatapathNICMac())
        sniff(
            filter=filterRE, iface=inIntf, prn=self.encap_callback4sfci2,
                count=1, store=0)

    def encap_callback4sfci2(self, frame):
        frame.show()
        condition = (frame[IP].src == SFF1_DATAPATH_IP 
                        and frame[IP].dst == SFCI2_0_EGRESS_IP
                        and frame[IP].proto == 0x04)
        assert condition
        outterPkt = frame.getlayer('IP')[0]
        innerPkt = frame.getlayer('IP')[1]
        assert innerPkt[IP].dst == WEBSITE_REAL_IP



    def verifyDirection1Traffic(self):
        self._sendDirection1Traffic2SFF()
        self._checkDecapsulatedTraffic(inIntf=TESTER_SERVER_INTF)

        self._sendDirection1Traffic2SFF4sfci2()
        self._checkDecapsulatedTraffic4sfci2(inIntf=TESTER_SERVER_INTF)

    def _sendDirection1Traffic2SFF(self):
        filePath = sendDirection1Traffic.__file__
        self.sP.runPythonScript(filePath)

    def _sendDirection1Traffic2SFF4sfci2(self):
        filePath = sendDirection1Traffic4sfci2.__file__
        self.sP.runPythonScript(filePath)

    def _checkDecapsulatedTraffic(self, inIntf):
        logging.info("_checkDecapsulatedTraffic: wait for packet")
        sniff(
            filter="ether dst " + str(self.server.getDatapathNICMac()),
            iface=inIntf, prn=self.decap_callback,count=1,store=0)

    def decap_callback(self, frame):
        frame.show()
        condition = (frame[IP].src == SFF1_DATAPATH_IP 
                        and frame[IP].dst == SFCI1_1_EGRESS_IP
                        and frame[IP].proto == 0x04)
        assert condition == True
        outterPkt = frame.getlayer('IP')[0]
        innerPkt = frame.getlayer('IP')[1]
        assert innerPkt[IP].src == WEBSITE_REAL_IP

    def _checkDecapsulatedTraffic4sfci2(self, inIntf):
        logging.info("_checkDecapsulatedTraffic: wait for packet")
        sniff(
            filter="ether dst " + str(self.server.getDatapathNICMac()),
            iface=inIntf, prn=self.decap_callback4sfci2,count=1,store=0)

    def decap_callback4sfci2(self, frame):
        frame.show()
        condition = (frame[IP].src == SFF1_DATAPATH_IP 
                        and frame[IP].dst == SFCI2_1_EGRESS_IP
                        and frame[IP].proto == 0x04)
        assert condition == True
        outterPkt = frame.getlayer('IP')[0]
        innerPkt = frame.getlayer('IP')[1]
        assert innerPkt[IP].src == WEBSITE_REAL_IP
