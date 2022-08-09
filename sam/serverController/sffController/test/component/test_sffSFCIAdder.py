#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
Usage:
    (1) sudo env "PATH=$PATH" python -m pytest ./test_sffSFCIAdder.py -s --disable-warnings
    (2) Please run 'python  ./serverAgent.py  0000:06:00.0  enp1s0  nfvi  2.2.0.98'
        on the NFVI running bess.
'''

import time

import pytest
from scapy.all import sniff, AsyncSniffer
from scapy.layers.l2 import ARP
from scapy.layers.inet import IP
from scapy.contrib.nsh import NSH

from sam.base.compatibility import screenInput
from sam.base.command import CMD_STATE_SUCCESSFUL
from sam.base.messageAgent import SFF_CONTROLLER_QUEUE, MEDIATOR_QUEUE, \
    MSG_TYPE_SFF_CONTROLLER_CMD, TURBONET_ZONE, MessageAgent
from sam.base.shellProcessor import ShellProcessor
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.test.fixtures.vnfControllerStub import VNFControllerStub
from sam.test.testBase import DIRECTION0_TRAFFIC_SPI, DIRECTION1_TRAFFIC_SPI, \
                        TestBase, CLASSIFIER_DATAPATH_IP, SFF1_CONTROLNIC_IP, \
                        SFF1_DATAPATH_IP, SFF1_DATAPATH_MAC, SFCI1_0_EGRESS_IP, \
                        WEBSITE_REAL_IP, SFCI1_1_EGRESS_IP
from sam.test.fixtures import sendArpRequest
from sam.serverController.sffController.test.component.testConfig import TESTER_SERVER_DATAPATH_IP, \
    TESTER_SERVER_DATAPATH_MAC, TESTER_DATAPATH_INTF, PRIVATE_KEY_FILE_PATH, BESS_SERVER_USER, \
    BESS_SERVER_USER_PASSWORD
from sam.serverController.sffController.sfcConfig import CHAIN_TYPE_NSHOVERETH, CHAIN_TYPE_UFRR, DEFAULT_CHAIN_TYPE
from sam.serverController.sffController.test.component.fixtures.sendDirection0Traffic import sendDirection0Traffic
from sam.serverController.sffController.test.component.fixtures.sendDirection1Traffic import sendDirection1Traffic


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
        self.vC.uninstallVNF(BESS_SERVER_USER, BESS_SERVER_USER_PASSWORD,
            SFF1_CONTROLNIC_IP, self.sfci.vnfiSequence[0][0].vnfiID, PRIVATE_KEY_FILE_PATH)
        self.killSFFController()

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

        # setup again
        try:
            # In normal case, there should be a timeout error!
            shellCmdRply = self.vC.installVNF(BESS_SERVER_USER, BESS_SERVER_USER_PASSWORD, 
                SFF1_CONTROLNIC_IP, self.sfci.vnfiSequence[0][0].vnfiID, PRIVATE_KEY_FILE_PATH)
            self.logger.info(
                "Error command reply:\n stdin:{0}\n stdout:{1}\n stderr:{2}".format(
                None,
                shellCmdRply['stdout'].read().decode('utf-8'),
                shellCmdRply['stderr'].read().decode('utf-8')))
        except Exception as ex:
            self.logger.info("If raise IOError: reading from stdin while output is captured")
            self.logger.info("Then pytest should use -s option!")
            ExceptionProcessor(self.logger).logException(ex)

        # verify again
        time.sleep(5)
        self.verifyDirection0Traffic()
        self.verifyDirection1Traffic()

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
            " and arp",iface=inIntf, prn=self.frame_callback,count=1,store=0)
        self.logger.info("Check arp response successfully!")

    def frame_callback(self,frame):
        frame.show()
        if frame[ARP].op == 2 and frame[ARP].psrc == SFF1_DATAPATH_IP:
            mac = frame[ARP].hwsrc
            assert mac.upper() == SFF1_DATAPATH_MAC.upper()

    def verifyDirection0Traffic(self):
        aSniffer = self._checkEncapsulatedTraffic(inIntf=TESTER_DATAPATH_INTF)
        time.sleep(2)
        self._sendDirection0Traffic2SFF()
        while True:
            if not aSniffer.running:
                break
        # aSniffer.stop()

    def _sendDirection0Traffic2SFF(self):
        # filePath = sendDirection0Traffic.__file__
        # self.sP.runPythonScript(filePath)
        sendDirection0Traffic()

    def _checkEncapsulatedTraffic(self,inIntf):
        self.logger.info("_checkEncapsulatedTraffic: wait for packet")
        filterRE = "ether dst " + str(self.server.getDatapathNICMac())
        aSniffer = AsyncSniffer(filter=filterRE,
            iface=inIntf, prn=self.encap_callback,count=1,store=0)
        # aSniffer = AsyncSniffer(
        #     iface=inIntf, prn=self.encap_callback,count=2,store=0)
        aSniffer.start()
        return aSniffer

    def encap_callback(self,frame):
        self.logger.info("Get encap back packet!")
        frame.show()
        if DEFAULT_CHAIN_TYPE == CHAIN_TYPE_UFRR:
            condition = (frame[IP].src == SFF1_DATAPATH_IP \
                and frame[IP].dst == SFCI1_0_EGRESS_IP \
                and frame[IP].proto == 0x04)
            assert condition == True
            outterPkt = frame.getlayer('IP')[0]
            innerPkt = frame.getlayer('IP')[1]
            assert innerPkt[IP].dst == WEBSITE_REAL_IP
        elif DEFAULT_CHAIN_TYPE == CHAIN_TYPE_NSHOVERETH:
            condition = (frame[NSH].spi == DIRECTION0_TRAFFIC_SPI \
                and frame[NSH].si == 0 \
                and frame[NSH].nextproto == 0x1)
            assert condition == True
            innerPkt = frame.getlayer('IP')[0]
            assert innerPkt[IP].dst == WEBSITE_REAL_IP
        else:
            raise ValueError("Unknown chain type {0}".format(DEFAULT_CHAIN_TYPE))

    def verifyDirection1Traffic(self):
        aSniffer = self._checkDecapsulatedTraffic(inIntf=TESTER_DATAPATH_INTF)
        time.sleep(2)
        self._sendDirection1Traffic2SFF()
        # aSniffer.stop()
        while True:
            if not aSniffer.running:
                break

    def _sendDirection1Traffic2SFF(self):
        # filePath = sendDirection1Traffic.__file__
        # self.sP.runPythonScript(filePath)
        sendDirection1Traffic()

    def _checkDecapsulatedTraffic(self,inIntf):
        self.logger.info("_checkDecapsulatedTraffic: wait for packet")
        aSniffer = AsyncSniffer(filter="ether dst " + str(self.server.getDatapathNICMac()),
            iface=inIntf, prn=self.decap_callback,count=1,store=0)
        aSniffer.start()
        return aSniffer

    def decap_callback(self,frame):
        self.logger.info("Get decap back packet!")
        frame.show()
        if DEFAULT_CHAIN_TYPE == CHAIN_TYPE_UFRR:
            condition = (frame[IP].src == SFF1_DATAPATH_IP and \
                frame[IP].dst == SFCI1_1_EGRESS_IP and frame[IP].proto == 0x04)
            assert condition == True
            outterPkt = frame.getlayer('IP')[0]
            innerPkt = frame.getlayer('IP')[1]
            assert innerPkt[IP].src == WEBSITE_REAL_IP
        elif DEFAULT_CHAIN_TYPE == CHAIN_TYPE_NSHOVERETH:
            condition = (frame[NSH].spi == DIRECTION1_TRAFFIC_SPI \
                and frame[NSH].si == 0 \
                and frame[NSH].nextproto == 0x1)
            assert condition == True
            innerPkt = frame.getlayer('IP')[0]
            assert innerPkt[IP].src == WEBSITE_REAL_IP

    def verifyCmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        self.logger.info("Verify cmy rply successfully!")
