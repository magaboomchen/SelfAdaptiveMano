#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid
import logging

from sam.base.slo import SLO
from sam.base.vnf import VNFI, VNF_TYPE_FORWARD
from sam.base.sfc import SFC, SFCI, APP_TYPE_NORTHSOUTH_WEBSITE
from sam.base.command import Command, CMD_STATE_SUCCESSFUL, \
    CMD_TYPE_HANDLE_SERVER_STATUS_CHANGE
from sam.base.messageAgent import SAMMessage, SERVER_CLASSIFIER_CONTROLLER_QUEUE, \
    NETWORK_CONTROLLER_QUEUE, MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, \
    MSG_TYPE_NETWORK_CONTROLLER_CMD, MEDIATOR_QUEUE, SFF_CONTROLLER_QUEUE, \
    MSG_TYPE_SFF_CONTROLLER_CMD, VNF_CONTROLLER_QUEUE, MSG_TYPE_VNF_CONTROLLER_CMD
from sam.base.server import Server, SERVER_TYPE_CLASSIFIER, SERVER_TYPE_NFVI
from sam.test.testBase import TestBase, CLASSIFIER_DATAPATH_IP, WEBSITE_REAL_IP

TESTER_SERVER_DATAPATH_MAC = "18:66:da:85:f9:ed"
OUTTER_CLIENT_IP = "1.1.1.2"
WEBSITE_REAL_IP = "3.3.3.3"

CLASSIFIER_DATAPATH_IP = "2.2.0.36"
CLASSIFIER_DATAPATH_MAC = "00:1b:21:c0:8f:ae"
CLASSIFIER_CONTROL_IP = "192.168.0.194"
CLASSIFIER_SERVERID = 10001

SFF1_DATAPATH_IP = "2.2.0.69"
SFF1_DATAPATH_MAC = "b8:ca:3a:65:f7:fa"
SFF1_CONTROLNIC_IP = "192.168.8.17"
SFF1_CONTROLNIC_MAC = "b8:ca:3a:65:f7:f8"
SFF1_SERVERID = 10003

SFF2_DATAPATH_IP = "2.2.0.71"
SFF2_DATAPATH_MAC = "ec:f4:bb:da:39:45"
SFF2_CONTROLNIC_IP = "192.168.8.18"
SFF2_CONTROLNIC_MAC = "ec:f4:bb:da:39:44"
SFF2_SERVERID = 10004

SFF3_DATAPATH_IP = "2.2.0.99"
SFF3_DATAPATH_MAC = "00:1b:21:c0:8f:98"
SFF3_CONTROLNIC_IP = "192.168.0.173"
SFF3_CONTROLNIC_MAC = "18:66:da:85:1c:c3"
SFF3_SERVERID = 10005


class TestbedFRR(TestBase):
    def addSFCI2Classifier(self):
        logging.info("setup add SFCI to classifier")
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SERVER_CLASSIFIER_CONTROLLER_QUEUE,
                        MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, self.addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def delSFCI2Classifier(self):
        logging.info("teardown delete SFCI to classifier")
        self.delSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SERVER_CLASSIFIER_CONTROLLER_QUEUE,
                        MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, self.delSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def addSFCI2SFF(self):
        logging.info("setup add SFCI to sff")
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SFF_CONTROLLER_QUEUE,
                        MSG_TYPE_SFF_CONTROLLER_CMD, self.addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def delSFCI2SFF(self):
        logging.info("teardown delete SFCI to sff")
        self.delSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SFF_CONTROLLER_QUEUE,
                        MSG_TYPE_SFF_CONTROLLER_CMD, self.delSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    # def sendHandleServerSoftwareFailureCmd(self):
    #     logging.info("sendHandleServerFailureCmd")
    #     server = Server("ens3", SFF1_DATAPATH_IP, SERVER_TYPE_NFVI)
    #     server.setServerID(SFF1_SERVERID)
    #     server.setControlNICIP(SFF1_CONTROLNIC_IP)
    #     server.setControlNICMAC(SFF1_CONTROLNIC_MAC)
    #     server.setDataPathNICMAC(SFF1_DATAPATH_MAC)
    #     msg = SAMMessage(MSG_TYPE_NETWORK_CONTROLLER_CMD,
    #         Command(
    #             cmdType=CMD_TYPE_HANDLE_SERVER_STATUS_CHANGE,
    #             cmdID=uuid.uuid1(),
    #             attributes={"serverDown":[server]}
    #         )
    #     )
    #     self._messageAgent.sendMsg(NETWORK_CONTROLLER_QUEUE, msg)

    def addVNFI2Server(self):
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(VNF_CONTROLLER_QUEUE,
                        MSG_TYPE_VNF_CONTROLLER_CMD, self.addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def delVNFI4Server(self):
        logging.warning("Deleting VNFI")
        self.delSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(VNF_CONTROLLER_QUEUE,
                        MSG_TYPE_VNF_CONTROLLER_CMD, self.delSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def addSFC2NetworkController(self):
        self.addSFCCmd.cmdID = uuid.uuid1()
        self.sendCmd(NETWORK_CONTROLLER_QUEUE,
                    MSG_TYPE_NETWORK_CONTROLLER_CMD,
                    self.addSFCCmd)
        # verify
        logging.info("Start listening on mediator queue")
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCCmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def addSFCI2NetworkController(self):
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(NETWORK_CONTROLLER_QUEUE,
                        MSG_TYPE_NETWORK_CONTROLLER_CMD,
                        self.addSFCICmd)
        # verify
        logging.info("Start listening on mediator queue")
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def genClassifier(self, datapathIfIP):
        classifier = Server("br1", datapathIfIP, SERVER_TYPE_CLASSIFIER)
        classifier.setServerID(CLASSIFIER_SERVERID)
        classifier._serverDatapathNICIP = CLASSIFIER_DATAPATH_IP
        classifier._serverDatapathNICMAC = CLASSIFIER_DATAPATH_MAC
        classifier._ifSet["br1"] = {}
        classifier._ifSet["br1"]["IP"] = CLASSIFIER_CONTROL_IP
        return classifier

    def genUniDirectionSFC(self, classifier):
        sfcUUID = uuid.uuid1()
        vNFTypeSequence = [VNF_TYPE_FORWARD]
        maxScalingInstanceNumber = 1
        backupInstanceNumber = 0
        applicationType = APP_TYPE_NORTHSOUTH_WEBSITE
        direction1 = {
            'ID': 0,
            'source': {"IPv4":"*", "node":None},
            'ingress': classifier,
            'match': {'srcIP': "*",'dstIP': WEBSITE_REAL_IP,
                'srcPort': "*",'dstPort': "*",'proto': "*"},
            'egress': classifier,
            'destination': {"IPv4": WEBSITE_REAL_IP, "node":None}
        }
        directions = [direction1]
        slo = SLO(latency=35, throughput=10)
        return SFC(sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
                    backupInstanceNumber, applicationType, directions, slo=slo)

    def genUniDirection12BackupSFCI(self):
        vnfiSequence = self.gen12BackupVNFISequence()
        return SFCI(self.assignSFCIID(), vnfiSequence, None,
                    self.genUniDirection12BackupForwardingPathSet())

    def gen12BackupVNFISequence(self, SFCLength=1):
        # hard-code function
        vnfiSequence = []
        for index in range(SFCLength):
            vnfiSequence.append([])

            server = Server("ens3", SFF1_DATAPATH_IP, SERVER_TYPE_NFVI)
            server.setServerID(SFF1_SERVERID)
            server.setControlNICIP(SFF1_CONTROLNIC_IP)
            server.setControlNICMAC(SFF1_CONTROLNIC_MAC)
            server.setDataPathNICMAC(SFF1_DATAPATH_MAC)
            server.updateResource()
            vnfi = VNFI(vnfID=VNF_TYPE_FORWARD, vnfType=VNF_TYPE_FORWARD, 
                vnfiID=uuid.uuid1(), node=server)
            vnfiSequence[index].append(vnfi)

            server = Server("ens3", SFF2_DATAPATH_IP, SERVER_TYPE_NFVI)
            server.setServerID(SFF2_SERVERID)
            server.setControlNICIP(SFF2_CONTROLNIC_IP)
            server.setControlNICMAC(SFF2_CONTROLNIC_MAC)
            server.setDataPathNICMAC(SFF2_DATAPATH_MAC)
            server.updateResource()
            vnfi = VNFI(vnfID=VNF_TYPE_FORWARD, vnfType=VNF_TYPE_FORWARD,
                vnfiID=uuid.uuid1(), node=server)
            vnfiSequence[index].append(vnfi)

            server = Server("ens3", SFF3_DATAPATH_IP, SERVER_TYPE_NFVI)
            server.setServerID(SFF3_SERVERID)
            server.setControlNICIP(SFF3_CONTROLNIC_IP)
            server.setControlNICMAC(SFF3_CONTROLNIC_MAC)
            server.setDataPathNICMAC(SFF3_DATAPATH_MAC)
            server.updateResource()
            vnfi = VNFI(vnfID=VNF_TYPE_FORWARD, vnfType=VNF_TYPE_FORWARD,
                vnfiID=uuid.uuid1(), node=server)
            vnfiSequence[index].append(vnfi)

        return vnfiSequence

    def sendHandleServerSoftwareFailureCmd(self):
        logging.info("sendHandleServerFailureCmd")
        server = Server("ens3", SFF1_DATAPATH_IP, SERVER_TYPE_NFVI)
        server.setServerID(SFF1_SERVERID)
        server.setControlNICIP(SFF1_CONTROLNIC_IP)
        server.setControlNICMAC(SFF1_CONTROLNIC_MAC)
        server.setDataPathNICMAC(SFF1_DATAPATH_MAC)
        msg = SAMMessage(MSG_TYPE_NETWORK_CONTROLLER_CMD,
            Command(
                cmdType=CMD_TYPE_HANDLE_SERVER_STATUS_CHANGE,
                cmdID=uuid.uuid1(),
                attributes={"serverDown":[server]}
            )
        )
        self._messageAgent.sendMsg(NETWORK_CONTROLLER_QUEUE, msg)
