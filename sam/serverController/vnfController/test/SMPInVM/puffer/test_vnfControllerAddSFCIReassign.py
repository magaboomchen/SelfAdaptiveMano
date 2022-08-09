#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid

import pytest
from scapy.all import sniff
from scapy.layers.inet import IP

from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.messageAgent import VNF_CONTROLLER_QUEUE, MSG_TYPE_VNF_CONTROLLER_CMD, \
    SFF_CONTROLLER_QUEUE, MSG_TYPE_SFF_CONTROLLER_CMD, MEDIATOR_QUEUE
from sam.base.vnf import VNFI, VNF_TYPE_FORWARD
from sam.base.server import Server, SERVER_TYPE_NORMAL
from sam.serverController.serverManager.serverManager import SERVERID_OFFSET
from sam.base.command import CMD_STATE_SUCCESSFUL
from sam.base.shellProcessor import ShellProcessor
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.test.testBase import TestBase, WEBSITE_REAL_IP, \
    TESTER_SERVER_DATAPATH_MAC, CLASSIFIER_DATAPATH_IP, SFCI1_0_EGRESS_IP, \
    SFCI1_1_EGRESS_IP

TESTER_SERVER_DATAPATH_IP = "2.2.0.199"
TESTER_SERVER_DATAPATH_MAC = "52:54:00:a8:b0:a1"

SFF0_DATAPATH_IP = "2.2.0.200"
SFF0_DATAPATH_MAC = "52:54:00:5a:14:f0"
SFF0_CONTROLNIC_IP = "192.168.0.201"
SFF0_CONTROLNIC_MAC = "52:54:00:1f:51:12"


class TestVNFSFCIAdderClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_addSFCI(self):
        # setup
        logConfigur = LoggerConfigurator(__name__,
            './log', 'testVNFSFCIAdder.log', level='debug')
        self.logger = logConfigur.getLogger()

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

        # setup
        self.runVNFController()
        self.runSFFController()

        yield
        # teardown
        self.delVNFI4Server()
        self.killSFFController()
        self.killVNFController()

    def _reassignVNFI2SFCI(self):
        vnfiID = self.sfci1.vnfiSequence[0][0].vnfiID
        self.sfci2.vnfiSequence[0][0].vnfiID = vnfiID

    def gen10BackupVNFISequence(self, SFCLength=1):
        # hard-code function
        vnfiSequence = []
        for index in range(SFCLength):
            vnfiSequence.append([])
            for iN in range(1):
                server = Server("ens3", SFF0_DATAPATH_IP, SERVER_TYPE_NORMAL)
                server.setServerID(SERVERID_OFFSET + 1)
                server.setControlNICIP(SFF0_CONTROLNIC_IP)
                server.setControlNICMAC(SFF0_CONTROLNIC_MAC)
                server.setDataPathNICMAC(SFF0_DATAPATH_MAC)
                server.updateResource()
                vnfi = VNFI(VNF_TYPE_FORWARD, vnfType=VNF_TYPE_FORWARD, 
                            vnfiID=uuid.uuid1(), node=server)
                vnfiSequence[index].append(vnfi)
        return vnfiSequence

    def test_addSFCIReassignVNFI(self, setup_addSFCI):
        # exercise
        self.logger.info("exercise")
        self.addSFCI1()
        self.addSFCI2()

        # verifiy
        self.verifyDirection0Traffic()
        self.verifyDirection1Traffic()

    def addSFCI1(self):
        self.addSFCI1Cmd = self.mediator.genCMDAddSFCI(self.sfc1, self.sfci1)
        self.sendCmd(SFF_CONTROLLER_QUEUE, MSG_TYPE_SFF_CONTROLLER_CMD, self.addSFCI1Cmd)
        self.verifyCmd1Rply()

        self.addSFCI1Cmd.cmdID = uuid.uuid1()
        self.sendCmd(VNF_CONTROLLER_QUEUE, MSG_TYPE_VNF_CONTROLLER_CMD, self.addSFCI1Cmd)
        self.verifyCmd1Rply()

    def addSFCI2(self):
        self.addSFCI2Cmd = self.mediator.genCMDAddSFCI(self.sfc2, self.sfci2)
        self.sendCmd(SFF_CONTROLLER_QUEUE, MSG_TYPE_SFF_CONTROLLER_CMD, self.addSFCI2Cmd)
        self.verifyCmd2Rply()

        self.addSFCI2Cmd.cmdID = uuid.uuid1()
        self.sendCmd(VNF_CONTROLLER_QUEUE, MSG_TYPE_VNF_CONTROLLER_CMD, self.addSFCI2Cmd)
        self.verifyCmd2Rply()

    def verifyCmd1Rply(self):
        # verify cmd1
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCI1Cmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def verifyCmd2Rply(self):
        # verify cmd2
        self.logger.info("verify cmd2")
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCI2Cmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def verifyDirection0Traffic(self):
        self._sendDirection0Traffic2SFF()
        self._checkEncapsulatedTraffic(inIntf="ens8")

    def _sendDirection0Traffic2SFF(self):
        filePath = "../fixtures/sendDirection0Traffic.py"
        self.sP.runPythonScript(filePath)

    def _checkEncapsulatedTraffic(self,inIntf):
        self.logger.info("_checkEncapsulatedTraffic: wait for packet")
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
        assert innerPkt[IP].dst == WEBSITE_REAL_IP

    def verifyDirection1Traffic(self):
        self._sendDirection1Traffic2SFF()
        self._checkDecapsulatedTraffic(inIntf="ens8")

    def _sendDirection1Traffic2SFF(self):
        filePath = "../fixtures/sendDirection1Traffic.py"
        self.sP.runPythonScript(filePath)

    def _checkDecapsulatedTraffic(self,inIntf):
        self.logger.info("_checkDecapsulatedTraffic: wait for packet")
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
        assert innerPkt[IP].src == WEBSITE_REAL_IP

    def delVNFI4Server(self):
        self.logger.warning("Deleting VNFII")
        self.delSFCICmd = self.mediator.genCMDDelSFCI(self.sfc1, self.sfci1)
        self.sendCmd(VNF_CONTROLLER_QUEUE, MSG_TYPE_VNF_CONTROLLER_CMD, self.delSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
