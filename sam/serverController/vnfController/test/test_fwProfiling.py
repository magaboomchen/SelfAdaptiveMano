#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging
from scapy.all import *
import time

import pytest

from sam.base import server
from sam.base.sfc import *
from sam.base.vnf import *
from sam.base.server import *
from sam.base.command import *
from sam.base.acl import *
from sam.base.socketConverter import *
from sam.base.shellProcessor import ShellProcessor
from sam.test.fixtures.mediatorStub import *
from sam.test.fixtures.vnfControllerStub import *
from sam.test.testBase import *
from sam.serverController.classifierController import *

MANUAL_TEST = True
TESTER_SERVER_DATAPATH_IP = "2.2.0.36"
TESTER_SERVER_DATAPATH_MAC = "f4:e9:d4:a3:53:a0"

SFF0_DATAPATH_IP = "2.2.0.38"
SFF0_DATAPATH_MAC = "00:1b:21:c0:8f:98"
SFF0_CONTROLNIC_IP = "192.168.0.173"
SFF0_CONTROLNIC_MAC = "18:66:da:85:1c:c3"

logging.basicConfig(level=logging.INFO)
logging.getLogger("pika").setLevel(logging.WARNING)

class TestVNFAddFW(TestBase):
    @pytest.fixture(scope="function")
    def setup_addFW(self):
        # setup
        self.sP = ShellProcessor()
        self.clearQueue()

        rabbitMQFilePath = server.__file__.split("server.py")[0] \
            + "rabbitMQConf.conf"
        logging.info(rabbitMQFilePath)
        self.resetRabbitMQConf(rabbitMQFilePath, "192.168.0.194",
            "mq", "123456")

        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genBiDirectionSFC(classifier, vnfTypeSeq=[VNF_TYPE_FW])
        self.sfci = self.genBiDirection10BackupSFCI()
        self.server = self.genTesterServer(TESTER_SERVER_DATAPATH_IP,
            TESTER_SERVER_DATAPATH_MAC)
        self.mediator = MediatorStub()

        self.runSFFController()
        self.runVNFController()

        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.sfci)
        self.addSFCI2SFF()

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
                config['ACL'] = self.genTestFWRules()
                vnfi = VNFI(VNF_TYPE_FW, VNFType=VNF_TYPE_FW, 
                    VNFIID=uuid.uuid1(), config=config, node=server)
                VNFISequence[index].append(vnfi)
        return VNFISequence

    def genTestFWRules(self):
        rules = []
        rules.append(ACLTuple(ACL_ACTION_ALLOW, proto=ACL_PROTO_TCP, srcAddr=OUTTER_CLIENT_IP, dstAddr=WEBSITE_REAL_IP, 
            srcPort=(1234, 1234), dstPort=(80, 80)))
        rules.append(ACLTuple(ACL_ACTION_ALLOW, proto=ACL_PROTO_TCP, srcAddr=WEBSITE_REAL_IP, dstAddr=OUTTER_CLIENT_IP,
            srcPort=(80, 80), dstPort=(1234, 1234)))
        rules.append(ACLTuple(ACL_ACTION_DENY))
        return rules


    def addSFCI2SFF(self):
        logging.info("setup add SFCI to sff")
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SFF_CONTROLLER_QUEUE,
            MSG_TYPE_SSF_CONTROLLER_CMD , self.addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def delVNFI4Server(self):
        logging.warning("DeletingÂ VNFI")
        self.delSFCICmd = self.mediator.genCMDDelSFCI(self.sfc, self.sfci)
        self.sendCmd(VNF_CONTROLLER_QUEUE, MSG_TYPE_VNF_CONTROLLER_CMD, self.delSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def test_addFW(self, setup_addFW):
        # exercise
        logging.info("exercise")
        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.sfci)
        self.sendCmd(VNF_CONTROLLER_QUEUE,
            MSG_TYPE_VNF_CONTROLLER_CMD , self.addSFCICmd)

        # verifiy
        self.verifyCmdRply()
        # self.verifyDirection0Traffic()
        # self.verifyDirection1Traffic()
        logging.info("please press any key to quit.")
        raw_input()

    def verifyDirection0Traffic(self):
        self._sendDirection0Traffic2SFF()
        self._checkEncapsulatedTraffic(inIntf="ens8")

    def _sendDirection0Traffic2SFF(self):
        filePath = "./fixtures/sendFWDirection0Traffic.py"
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
        assert innerPkt[IP].dst == WEBSITE_REAL_IP

    def verifyDirection1Traffic(self):
        self._sendDirection1Traffic2SFF()
        self._checkDecapsulatedTraffic(inIntf="ens8")

    def _sendDirection1Traffic2SFF(self):
        filePath = "./fixtures/sendFWDirection1Traffic.py"
        self.sP.runPythonScript(filePath)

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
        assert innerPkt[IP].src == WEBSITE_REAL_IP


    def verifyCmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

