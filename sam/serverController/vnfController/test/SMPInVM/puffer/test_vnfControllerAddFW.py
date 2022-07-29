#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid
import logging

import pytest
from scapy.all import sniff
from scapy.layers.inet import IP, TCP

from sam import base
from sam.base.messageAgent import VNF_CONTROLLER_QUEUE, MSG_TYPE_VNF_CONTROLLER_CMD, \
    SFF_CONTROLLER_QUEUE, MSG_TYPE_SFF_CONTROLLER_CMD, MEDIATOR_QUEUE
from sam.base.routingMorphic import IPV4_ROUTE_PROTOCOL
from sam.base.vnf import VNFI, VNF_TYPE_FW
from sam.base.server import Server, SERVER_TYPE_NORMAL
from sam.serverController.serverManager.serverManager import SERVERID_OFFSET
from sam.base.command import CMD_STATE_SUCCESSFUL
from sam.base.acl import ACLTable, ACLTuple, ACL_ACTION_ALLOW, ACL_PROTO_TCP
from sam.base.shellProcessor import ShellProcessor
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.test.testBase import TestBase, WEBSITE_REAL_IP, OUTTER_CLIENT_IP, \
    TESTER_SERVER_DATAPATH_MAC, CLASSIFIER_DATAPATH_IP, SFCI1_0_EGRESS_IP, \
    SFCI1_1_EGRESS_IP

MANUAL_TEST = True
TESTER_SERVER_DATAPATH_IP = "2.2.0.199"
TESTER_SERVER_DATAPATH_MAC = "52:54:00:a8:b0:a1"

SFF0_DATAPATH_IP = "2.2.0.200"
SFF0_DATAPATH_MAC = "52:54:00:5a:14:f0"
SFF0_CONTROLNIC_IP = "192.168.0.201"
SFF0_CONTROLNIC_MAC = "52:54:00:1f:51:12"

logging.basicConfig(level=logging.INFO)


class TestVNFAddFW(TestBase):
    @pytest.fixture(scope="function")
    def setup_addFW(self):
        # setup
        self.resetRabbitMQConf(
            base.__file__[:base.__file__.rfind("/")] + "/rabbitMQConf.json",
            "192.168.0.158", "mq", "123456")
        self.sP = ShellProcessor()
        self.clearQueue()
        self.killAllModule()

        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genBiDirectionSFC(classifier, vnfTypeSeq=[VNF_TYPE_FW])
        self.sfci = self.genBiDirection10BackupSFCI()
        self.mediator = MediatorStub()

        self.server = self.genTesterServer(TESTER_SERVER_DATAPATH_IP,
            TESTER_SERVER_DATAPATH_MAC)

        self.runSFFController()
        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.sfci)
        self.addSFCI2SFF()

        # setup
        self.runVNFController()

        yield
        # teardown
        self.delVNFI4Server()
        self.killSFFController()
        self.killVNFController()

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
                config = self.genTestIPv4FWRules()
                vnfi = VNFI(VNF_TYPE_FW, vnfType=VNF_TYPE_FW, 
                    vnfiID=uuid.uuid1(), config=config, node=server)
                vnfiSequence[index].append(vnfi)
        return vnfiSequence

    def genTestIPv4FWRules(self):
        entry1 = ACLTuple(ACL_ACTION_ALLOW, proto=ACL_PROTO_TCP, srcAddr=OUTTER_CLIENT_IP, dstAddr=WEBSITE_REAL_IP, 
            srcPort=(1234, 1234), dstPort=(80, 80))
        entry2 = ACLTuple(ACL_ACTION_ALLOW, proto=ACL_PROTO_TCP, srcAddr=WEBSITE_REAL_IP, dstAddr=OUTTER_CLIENT_IP,
            srcPort=(80, 80), dstPort=(1234, 1234))
        entry3 = ACLTuple(ACL_ACTION_ALLOW)
        aclT = ACLTable()
        aclT.addRules(entry1, IPV4_ROUTE_PROTOCOL)
        aclT.addRules(entry2, IPV4_ROUTE_PROTOCOL)
        aclT.addRules(entry3, IPV4_ROUTE_PROTOCOL)
        return aclT

    def addSFCI2SFF(self):
        logging.info("setup add SFCI to sff")
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SFF_CONTROLLER_QUEUE,
            MSG_TYPE_SFF_CONTROLLER_CMD , self.addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    '''
    def addVNFI2Server(self):
        logging.info("setup add SFCI to server")
        try:
            # In normal case, there should be a timeout error!
            shellCmdRply = self.vC.installVNF("t1", "t1@netlab325", "192.168.0.156",
                self.sfci.vnfiSequence[0][0].vnfiID)
            logging.info(
                "command reply:\n stdin:{0}\n stdout:{1}\n stderr:{2}".format(
                None,
                shellCmdRply['stdout'].read().decode('utf-8'),
                shellCmdRply['stderr'].read().decode('utf-8')))
        except:
            logging.info("If raise IOError: reading from stdin while output is captured")
            logging.info("Then pytest should use -s option!")
    '''

    def delVNFI4Server(self):
        logging.warning("Deleting VNFII")
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
        self.verifyDirection0Traffic()
        self.verifyDirection1Traffic()

    def verifyDirection0Traffic(self):
        self._sendDirection0Traffic2SFF()
        self._checkEncapsulatedTraffic(inIntf="ens8")

    def _sendDirection0Traffic2SFF(self):
        filePath = "../fixtures/sendFWDirection0Traffic.py"
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
        filePath = "../fixtures/sendFWDirection1Traffic.py"
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

