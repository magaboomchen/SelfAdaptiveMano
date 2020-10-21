#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid
import subprocess
import time
import logging

from scapy.all import *
import psutil
import pytest

from sam.base.sfc import *
from sam.base.vnf import *
from sam.base.server import *
from sam.base.path import *
from sam.base.switch import *
from sam.base.server import *
from sam.base.link import *
from sam.serverController.classifierController import *
from sam.serverAgent.serverAgent import ServerAgent
from sam.serverController.serverManager.serverManager import *
from sam.base.command import *
from sam.base.socketConverter import *
from sam.base.shellProcessor import ShellProcessor
from sam.test.fixtures.mediatorStub import *
from sam.test.fixtures.orchestrationStub import *

OUTTER_CLIENT_IP = "1.1.1.1"
WEBSITE_REAL_IP = "2.2.0.34"

TEST_SERVERID = 19999

CLASSIFIER_DATAPATH_IP = "2.2.0.36"
CLASSIFIER_DATAPATH_MAC = "52:54:00:05:4D:7D"
CLASSIFIER_CONTROL_IP = "192.168.122.34"
CLASSIFIER_SERVERID = 10001

VNFI1_0_IP = "10.0.17.1"
VNFI1_1_IP = "10.0.17.128"
FW_VNFI1_0_IP = "10.0.18.1"
FW_VNFI1_1_IP = "10.0.18.128"
LB_VNFI1_0_IP = "10.0.21.1"
LB_VNFI1_1_IP = "10.0.21.128"
SFCI1_0_EGRESS_IP = "10.0.16.1"
SFCI1_1_EGRESS_IP = "10.0.16.128"

SFF1_DATAPATH_IP = "2.2.0.69"
SFF1_DATAPATH_MAC = "52:54:00:9D:F4:F4"
SFF1_CONTROLNIC_IP = "192.168.122.134"
SFF1_CONTROLNIC_MAC = "52:54:00:80:ea:94"

SFF2_DATAPATH_IP = "2.2.0.99"
SFF2_DATAPATH_MAC = "52:54:00:F7:34:25"
SFF2_CONTROLNIC_IP = "192.168.122.208"
SFF2_CONTROLNIC_MAC = "52:54:00:D5:A7:0C"

SFF3_DATAPATH_IP = "2.2.0.71"
SFF3_DATAPATH_MAC = "52:54:00:5a:14:f0"
SFF3_CONTROLNIC_IP = "192.168.122.135"
SFF3_CONTROLNIC_MAC = "52:54:00:1f:51:12"

logging.basicConfig(level=logging.INFO)

class TestBase(object):
    MAXSFCIID = 0

    def assignSFCIID(self):
        TestBase.MAXSFCIID = TestBase.MAXSFCIID + 1
        return TestBase.MAXSFCIID

    def genClassifier(self, datapathIfIP):
        classifier = Server("ens3", datapathIfIP, SERVER_TYPE_CLASSIFIER)
        classifier.setServerID(CLASSIFIER_SERVERID)
        classifier._serverDatapathNICIP = CLASSIFIER_DATAPATH_IP
        classifier._ifSet["ens3"] = {}
        classifier._ifSet["ens3"]["IP"] = CLASSIFIER_CONTROL_IP
        classifier._serverDatapathNICMAC = CLASSIFIER_DATAPATH_MAC
        return classifier

    def genTesterServer(self, datapathIfIP, datapathIfMac):
        server = Server("virbr0", datapathIfIP, SERVER_TYPE_TESTER)
        server.setServerID(TEST_SERVERID)
        server.updateControlNICMAC()
        server.updateIfSet()
        server._serverDatapathNICMAC = datapathIfMac
        return server

    def runClassifierController(self):
        filePath = "~/HaoChen/Project/SelfAdaptiveMano/sam/serverController/classifierController/classifierControllerCommandAgent.py"
        self.sP.runPythonScript(filePath)

    def killClassifierController(self):
        self.sP.killPythonScript("classifierControllerCommandAgent.py")

    def runSFFController(self):
        filePath = "~/HaoChen/Project/SelfAdaptiveMano/sam/serverController/sffController/sffControllerCommandAgent.py"
        self.sP.runPythonScript(filePath)

    def killSFFController(self):
        self.sP.killPythonScript("sffControllerCommandAgent.py")

    def runVNFController(self):
        filePath = "~/HaoChen/Project/SelfAdaptiveMano/sam/serverController/vnfController/vnfController.py"
        self.sP.runPythonScript(filePath)

    def killVNFController(self):
        self.sP.killPythonScript("vnfController.py")

    def genUniDirectionSFC(self, classifier):
        sfcUUID = uuid.uuid1()
        vNFTypeSequence = [VNF_TYPE_FORWARD]
        maxScalingInstanceNumber = 1
        backupInstanceNumber = 0
        applicationType = APP_TYPE_NORTHSOUTH_WEBSITE
        direction1 = {
            'ID': 0,
            'source': None,
            'ingress': classifier,
            'match': {'srcIP': None,'dstIP':WEBSITE_REAL_IP,
                'srcPort': None,'dstPort': None,'proto': None},
            'egress': classifier,
            'destination': {"IPv4":WEBSITE_REAL_IP}
        }
        directions = [direction1]
        return SFC(sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
            backupInstanceNumber, applicationType, directions, {'zone':""})

    def genBiDirectionSFC(self, classifier, vnfTypeSeq=[VNF_TYPE_FORWARD]):
        sfcUUID = uuid.uuid1()
        vNFTypeSequence = vnfTypeSeq
        maxScalingInstanceNumber = 1
        backupInstanceNumber = 0
        applicationType = APP_TYPE_NORTHSOUTH_WEBSITE
        direction1 = {
            'ID': 0,
            'source': None,
            'ingress': classifier,
            'match': {'srcIP': None,'dstIP':WEBSITE_REAL_IP,
                'srcPort': None,'dstPort': None,'proto': None},
            'egress': classifier,
            'destination': {"IPv4":WEBSITE_REAL_IP}
        }
        direction2 = {
            'ID': 1,
            'source': {"IPv4":WEBSITE_REAL_IP},
            'ingress': classifier,
            'match': {'srcIP': WEBSITE_REAL_IP,'dstIP':None,
                'srcPort': None,'dstPort': None,'proto': None},
            'egress': classifier,
            'destination': None
        }
        directions = [direction1,direction2]
        return SFC(sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
            backupInstanceNumber, applicationType, directions, {'zone':""})

    def genUniDirection10BackupSFCI(self):
        VNFISequence = self.gen10BackupVNFISequence()
        return SFCI(self.assignSFCIID(), VNFISequence, None,
            self.genUniDirection10BackupForwardingPathSet())

    def genBiDirection10BackupSFCI(self):
        VNFISequence = self.gen10BackupVNFISequence()
        return SFCI(self.assignSFCIID(), VNFISequence, None,
            self.genBiDirection10BackupForwardingPathSet())

    def genUniDirection11BackupSFCI(self):
        VNFISequence = self.gen11BackupVNFISequence()
        return SFCI(self.assignSFCIID(), VNFISequence, None,
            self.genUniDirection11BackupForwardingPathSet())

    def gen10BackupVNFISequence(self, SFCLength=1):
        # hard-code function
        VNFISequence = []
        for index in range(SFCLength):
            VNFISequence.append([])
            for iN in range(1):
                server = Server("ens3",SFF1_DATAPATH_IP,SERVER_TYPE_NORMAL)
                server.setServerID(SERVERID_OFFSET + 1)
                server.setControlNICIP(SFF1_CONTROLNIC_IP)
                server.setControlNICMAC(SFF1_CONTROLNIC_MAC)
                server.setDataPathNICMAC(SFF1_DATAPATH_MAC)
                vnfi = VNFI(VNF_TYPE_FORWARD, VNFType=VNF_TYPE_FORWARD,
                    VNFIID=uuid.uuid1(), node=server)
                VNFISequence[index].append(vnfi)
        return VNFISequence

    def gen11BackupVNFISequence(self, SFCLength=1):
        # hard-code function
        VNFISequence = []
        for index in range(SFCLength):
            VNFISequence.append([])
            
            server = Server("ens3",SFF1_DATAPATH_IP,SERVER_TYPE_NORMAL)
            server.setServerID(SERVERID_OFFSET + 1)
            server.setControlNICIP(SFF1_CONTROLNIC_IP)
            server.setControlNICMAC(SFF1_CONTROLNIC_MAC)
            server.setDataPathNICMAC(SFF1_DATAPATH_MAC)
            vnfi = VNFI(VNFID=VNF_TYPE_FORWARD, VNFType=VNF_TYPE_FORWARD,
                VNFIID=uuid.uuid1(), node=server)
            VNFISequence[index].append(vnfi)

            server = Server("ens3",SFF2_DATAPATH_IP,SERVER_TYPE_NORMAL)
            server.setServerID(SERVERID_OFFSET + 2)
            server.setControlNICIP(SFF2_CONTROLNIC_IP)
            server.setControlNICMAC(SFF2_CONTROLNIC_MAC)
            server.setDataPathNICMAC(SFF2_DATAPATH_MAC)
            vnfi = VNFI(VNFID=VNF_TYPE_FORWARD, VNFType=VNF_TYPE_FORWARD,
                VNFIID=uuid.uuid1(), node=server)
            VNFISequence[index].append(vnfi)

        return VNFISequence

    def genUniDirection10BackupForwardingPathSet(self):
        primaryForwardingPath = {1:[[10001,1,2,10002],[10002,2,1,10001]]}
        frrType = "UFRR"
        # {(srcID,dstID,pathID):forwardingPath}
        backupForwardingPath = {
            1:{(1,2,2):[[1,3,2,10002],[10002,2,3,1,10001]]}
        }
        return ForwardingPathSet(primaryForwardingPath,frrType,
            backupForwardingPath)

    def genUniDirection11BackupForwardingPathSet(self):
        primaryForwardingPath = {1:[[10001,1,2,10002],[10002,2,1,10001]]}
        frrType = "UFRR"
        # {(srcID,dstID,pathID):forwardingPath}
        backupForwardingPath = {
            1:{(1,2,2):[[1,3,10003],[10003,3,1,10001]],
                (2,10002,3):[[2,3,10003],[10003,3,1,10001]]
            }
        }
        return ForwardingPathSet(primaryForwardingPath,frrType,
            backupForwardingPath)

    def genBiDirection10BackupForwardingPathSet(self):
        primaryForwardingPath = {
            1:[[10001,1,2,10002],[10002,2,1,10001]],
            128:[[10001,1,2,10002],[10002,2,1,10001]]
        }
        frrType = "UFRR"
        # {(srcID,dstID,pathID):forwardingPath}
        backupForwardingPath = {
            1:{(1,2,2):[[1,3,2,10002],[10002,2,3,1,10001]]
            },
            128:{
                (1,2,129):[[1,3,2,10002],[10002,2,3,1,10001]]
            }
        }
        return ForwardingPathSet(primaryForwardingPath,frrType,
            backupForwardingPath)

    def genUniDirection12BackupSFCI(self):
        VNFISequence = self.gen12BackupVNFISequence()
        return SFCI(self.assignSFCIID(),VNFISequence, None,
            self.genUniDirection12BackupForwardingPathSet())

    def gen12BackupVNFISequence(self, SFCLength=1):
        # hard-code function
        VNFISequence = []
        for index in range(SFCLength):
            VNFISequence.append([])

            server = Server("ens3", SFF1_DATAPATH_IP, SERVER_TYPE_NORMAL)
            server.setServerID(SERVERID_OFFSET + 1)
            server.setControlNICIP(SFF1_CONTROLNIC_IP)
            server.setControlNICMAC(SFF1_CONTROLNIC_MAC)
            server.setDataPathNICMAC(SFF1_DATAPATH_MAC)
            vnfi = VNFI(VNFID=VNF_TYPE_FORWARD, VNFType=VNF_TYPE_FORWARD, 
                VNFIID=uuid.uuid1(), node=server)
            VNFISequence[index].append(vnfi)

            server = Server("ens3", SFF2_DATAPATH_IP, SERVER_TYPE_NORMAL)
            server.setServerID(SERVERID_OFFSET + 2)
            server.setControlNICIP(SFF2_CONTROLNIC_IP)
            server.setControlNICMAC(SFF2_CONTROLNIC_MAC)
            server.setDataPathNICMAC(SFF2_DATAPATH_MAC)
            vnfi = VNFI(VNFID=VNF_TYPE_FORWARD, VNFType=VNF_TYPE_FORWARD,
                VNFIID=uuid.uuid1(), node=server)
            VNFISequence[index].append(vnfi)

            server = Server("ens3", SFF3_DATAPATH_IP, SERVER_TYPE_NORMAL)
            server.setServerID(SERVERID_OFFSET + 3)
            server.setControlNICIP(SFF3_CONTROLNIC_IP)
            server.setControlNICMAC(SFF3_CONTROLNIC_MAC)
            server.setDataPathNICMAC(SFF3_DATAPATH_MAC)
            vnfi = VNFI(VNFID=VNF_TYPE_FORWARD, VNFType=VNF_TYPE_FORWARD,
                VNFIID=uuid.uuid1(), node=server)
            VNFISequence[index].append(vnfi)

        return VNFISequence

    def genUniDirection12BackupForwardingPathSet(self):
        primaryForwardingPath = {1:[[10001,1,2,10002],[10002,2,1,10001]]}
        frrType = "UFRR"
        # {(srcID,dstID,pathID):forwardingPath}
        backupForwardingPath = {
            1:{(1,2,2):[[1,3,10003],[10003,3,1,10001]],
                (2,10002,3):[[2,10004],[10004,2,1,10001]]
            }
        }
        return ForwardingPathSet(primaryForwardingPath,frrType,
            backupForwardingPath)

    def recvCmd(self, queue):
        messageAgentTmp = MessageAgent()
        messageAgentTmp.startRecvMsg(queue)
        logging.info("testBase:recvCmd")
        while True:
            msg = messageAgentTmp.getMsg(queue)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            else:
                body = msg.getbody()
                if messageAgentTmp.isCommand(body):
                    return body
                else:
                    logging.error("Unknown massage body: {0}".format(
                        type(body)))
        del messageAgentTmp

    def recvCmdRply(self, queue):
        messageAgentTmp = MessageAgent()
        messageAgentTmp.startRecvMsg(queue)
        while True:
            msg = messageAgentTmp.getMsg(queue)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            else:
                body = msg.getbody()
                if messageAgentTmp.isCommandReply(body):
                    logging.info("testBase:recvCmdRply")
                    return body
                else:
                    logging.error("Unknown massage body")
        del messageAgentTmp

    def sendCmd(self, queue, msgType, cmd):
        messageAgentTmp = MessageAgent()
        msg = SAMMessage(msgType, cmd)
        messageAgentTmp.sendMsg(queue, msg)
        del messageAgentTmp

    def sendCmdRply(self, queue, msgType, cmdRply):
        messageAgentTmp = MessageAgent()
        msg = SAMMessage(msgType, cmdRply)
        messageAgentTmp.sendMsg(queue, msg)
        del messageAgentTmp

    def sendRequest(self, queue, request):
        messageAgentTmp = MessageAgent()
        msg = SAMMessage(MSG_TYPE_REQUEST, request)
        messageAgentTmp.sendMsg(queue, msg)
        del messageAgentTmp

    def recvReply(self, queue):
        messageAgentTmp = MessageAgent()
        messageAgentTmp.startRecvMsg(queue)
        while True:
            msg = messageAgentTmp.getMsg(queue)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            else:
                body = msg.getbody()
                if messageAgentTmp.isReply(body):
                    logging.info("testBase: recv a reply")
                    return body
                else:
                    logging.error("Unknown massage body")
        del messageAgentTmp

    def clearQueue(self):
        self.sP.runShellCommand("sudo rabbitmqctl purge_queue MEDIATOR_QUEUE")
        self.sP.runShellCommand(
            "sudo rabbitmqctl purge_queue MEASURER_QUEUE")
        self.sP.runShellCommand(
            "sudo rabbitmqctl purge_queue ORCHESTRATOR_QUEUE")
        self.sP.runShellCommand(
            "sudo rabbitmqctl purge_queue SFF_CONTROLLER_QUEUE")
        self.sP.runShellCommand(
            "sudo rabbitmqctl purge_queue VNF_CONTROLLER_QUEUE")
        self.sP.runShellCommand(
            "sudo rabbitmqctl purge_queue SERVER_MANAGER_QUEUE")
        self.sP.runShellCommand(
            "sudo rabbitmqctl purge_queue NETWORK_CONTROLLER_QUEUE")

    def genSwitchList(self, num, switchType, 
            switchLANNetlist, switchIDList):
        switches = []
        for i in range(num):
            switch = Switch(switchIDList[i], switchType, switchLANNetlist[i])
            switches.append(switch)
        return switches

    # def genLinkList(self, num):
    #     links = []
    #     for i in range(num):
    #         link = Link(i,(i+1)%num)
    #         links.append(link)
    #     return links

    def genServerList(self, num, serverType, serverCIPList,
            serverDPIPList, serverIDList):
        servers = []
        for i in range(num):
            server = Server("ens3",serverDPIPList[i], serverType)
            server.setServerID(serverIDList[i])
            server.setControlNICIP(serverCIPList[i])
            servers.append(server)
        return servers

    def genAddSFCIRequest(self, sfc):
        sfc.backupInstanceNumber = 3
        request = Request(0, uuid.uuid1(), REQUEST_TYPE_ADD_SFCI,
            REQUEST_PROCESSOR_QUEUE, REQUEST_STATE_INITIAL, {'sfc':sfc, 'zone':""})
        return request

