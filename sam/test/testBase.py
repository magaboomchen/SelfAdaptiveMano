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
from sam.base.command import *
from sam.base.socketConverter import *
from sam.base.routingMorphic import *
from sam.base.test.fixtures.ipv4MorphicDict import *
from sam.base.test.fixtures.ipv6MorphicDict import *
from sam.base.test.fixtures.geoMorphicDict import *
from sam.base.shellProcessor import ShellProcessor
from sam.test.fixtures.mediatorStub import *
from sam.test.fixtures.orchestrationStub import *
from sam.toolkit import cleanAllLogFile
from sam.toolkit import clearAllSAMQueue
from sam.toolkit import killAllSAMPythonScripts
from sam.serverController.classifierController import *
from sam.serverAgent.serverAgent import ServerAgent
from sam.serverController.serverManager.serverManager import *
from sam.serverController.classifierController import classifierControllerCommandAgent
from sam.serverController.sffController import sffControllerCommandAgent
from sam.serverController.vnfController import vnfController
from sam.serverController.serverManager import serverManager
from sam.orchestration import orchestrator
from sam.mediator import mediator
from sam.measurement import measurer

OUTTER_CLIENT_IP = "1.1.1.1"
WEBSITE_REAL_IP = "3.3.3.3"

TEST_SERVERID = 19999

TESTER_SERVER_DATAPATH_IP = "192.168.123.1"
TESTER_SERVER_DATAPATH_MAC = "fe:54:00:05:4d:7d"

CLASSIFIER_DATAPATH_IP = "2.2.0.36"
CLASSIFIER_DATAPATH_MAC = "52:54:00:05:4D:7D"
CLASSIFIER_CONTROL_IP = "192.168.122.34"
CLASSIFIER_SERVERID = 10001

VNFI1_0_IP = "10.16.1.1"
VNFI1_1_IP = "10.16.1.128"
FW_VNFI1_0_IP = "10.32.1.1"
FW_VNFI1_1_IP = "10.32.1.128"
MON_VNFI1_0_IP = "10.64.1.1"
MON_VNFI1_1_IP = "10.64.1.128"
LB_VNFI1_0_IP = "10.80.1.1"
LB_VNFI1_1_IP = "10.80.1.128"
NAT_VNFI1_0_IP = "10.112.1.1"
NAT_VNFI1_1_IP = "10.112.1.128"
VPN_VNFI1_0_IP = "10.128.1.1"
VPN_VNFI1_1_IP = "10.128.1.128"
SFCI1_0_EGRESS_IP = "10.0.1.1"
SFCI1_1_EGRESS_IP = "10.0.1.128"


SFF1_DATAPATH_IP = "2.2.0.69"
SFF1_DATAPATH_MAC = "52:54:00:ad:18:c2"
SFF1_CONTROLNIC_IP = "192.168.122.134"
SFF1_CONTROLNIC_MAC = "52:54:00:80:ea:94"
SFF1_SERVERID = 10003

SFF2_DATAPATH_IP = "2.2.0.71"
SFF2_DATAPATH_MAC = "52:54:00:7b:56:86"
SFF2_CONTROLNIC_IP = "192.168.122.135"
SFF2_CONTROLNIC_MAC = "52:54:00:1f:51:12"
SFF2_SERVERID = 10004

SFF3_DATAPATH_IP = "2.2.0.99"
SFF3_DATAPATH_MAC = "52:54:00:f7:34:25"
SFF3_CONTROLNIC_IP = "192.168.122.208"
SFF3_CONTROLNIC_MAC = "52:54:00:D5:A7:0C"
SFF3_SERVERID = 10005

logging.basicConfig(level=logging.INFO)


class TestBase(object):
    MAXSFCIID = 0
    sfciCounter = 0
    logging.getLogger("pika").setLevel(logging.WARNING)

    def resetRabbitMQConf(self, filePath, serverIP,
            serverUser, serverPasswd):
        with open(filePath, 'w') as f:
            f.write("RABBITMQSERVERIP = '{0}'\n".format(serverIP))
            f.write("RABBITMQSERVERUSER = '{0}'\n".format(serverUser))
            f.write("RABBITMQSERVERPASSWD = '{0}'\n".format(serverPasswd))

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
        filePath = classifierControllerCommandAgent.__file__
        self.sP.runPythonScript(filePath)

    def killClassifierController(self):
        self.sP.killPythonScript("classifierControllerCommandAgent.py")

    def runSFFController(self):
        filePath = sffControllerCommandAgent.__file__
        self.sP.runPythonScript(filePath)

    def killSFFController(self):
        self.sP.killPythonScript("sffControllerCommandAgent.py")

    def runVNFController(self):
        filePath = vnfController.__file__
        self.sP.runPythonScript(filePath)

    def killVNFController(self):
        self.sP.killPythonScript("vnfController.py")

    def killServerManager(self):
        self.sP.killPythonScript("serverManager.py")

    def killMediator(self):
        self.sP.killPythonScript("mediator.py")

    def runOrchestrator(self):
        filePath = orchestrator.__file__
        self.sP.runPythonScript(filePath)

    def runMeasurer(self):
        filePath = measurer.__file__
        self.sP.runPythonScript(filePath)

    def runMediator(self):
        filePath = mediator.__file__
        self.sP.runPythonScript(filePath)

    def runServerManager(self):
        filePath = serverManager.__file__
        self.sP.runPythonScript(filePath)

    def runMediator(self):
        filePath = mediator.__file__
        self.sP.runPythonScript(filePath)

    def genUniDirectionSFC(self, classifier):
        sfcUUID = uuid.uuid1()
        vNFTypeSequence = [VNF_TYPE_FORWARD]
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
        directions = [direction1]
        slo = SLO(latencyBound=35, throughput=10)
        return SFC(sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
            backupInstanceNumber, applicationType, directions,
            {'zone':""}, slo=slo)

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
            'match': {'srcIP': "*",'dstIP': WEBSITE_REAL_IP,
                'srcPort': "*",'dstPort': "*",'proto': "*"},
            'egress': classifier,
            'destination': {"IPv4": WEBSITE_REAL_IP}
        }
        direction2 = {
            'ID': 1,
            'source': {"IPv4": WEBSITE_REAL_IP},
            'ingress': classifier,
            'match': {'srcIP': WEBSITE_REAL_IP,'dstIP': "*",
                'srcPort': "*",'dstPort': "*",'proto': "*"},
            'egress': classifier,
            'destination': "*"
        }
        directions = [direction1, direction2]
        routingMorphic = RoutingMorphic()
        routingMorphic.from_dict(ipv4MorphicDictTemplate)
        return SFC(sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
            backupInstanceNumber, applicationType, directions=directions,
            attributes={'zone':""},
            # routingMorphic=MORPHIC_IPV4
            routingMorphic=routingMorphic
            )

    def genUniDirection10BackupSFCI(self):
        vnfiSequence = self.gen10BackupVNFISequence()
        return SFCI(self.assignSFCIID(), vnfiSequence, None,
            self.genUniDirection10BackupForwardingPathSet())

    def genBiDirection10BackupSFCI(self):
        vnfiSequence = self.gen10BackupVNFISequence()
        return SFCI(self.assignSFCIID(), vnfiSequence, None,
            self.genBiDirection10BackupForwardingPathSet())

    def genUniDirection11BackupSFCI(self):
        vnfiSequence = self.gen11BackupVNFISequence()
        return SFCI(self.assignSFCIID(), vnfiSequence, None,
            self.genUniDirection11BackupForwardingPathSet())

    def gen10BackupVNFISequence(self, SFCLength=1):
        # hard-code function
        vnfiSequence = []
        for index in range(SFCLength):
            vnfiSequence.append([])
            for iN in range(1):
                server = Server("ens3", SFF1_DATAPATH_IP, SERVER_TYPE_NFVI)
                server.setServerID(SFF1_SERVERID)
                server.setControlNICIP(SFF1_CONTROLNIC_IP)
                server.setControlNICMAC(SFF1_CONTROLNIC_MAC)
                server.setDataPathNICMAC(SFF1_DATAPATH_MAC)
                vnfi = VNFI(VNF_TYPE_FORWARD, vnfType=VNF_TYPE_FORWARD,
                    vnfiID=uuid.uuid1(), node=server)
                vnfiSequence[index].append(vnfi)
        return vnfiSequence

    def gen11BackupVNFISequence(self, SFCLength=1):
        # hard-code function
        vnfiSequence = []
        for index in range(SFCLength):
            vnfiSequence.append([])
            
            server = Server("ens3",SFF1_DATAPATH_IP, SERVER_TYPE_NFVI)
            server.setServerID(SFF1_SERVERID)
            server.setControlNICIP(SFF1_CONTROLNIC_IP)
            server.setControlNICMAC(SFF1_CONTROLNIC_MAC)
            server.setDataPathNICMAC(SFF1_DATAPATH_MAC)
            vnfi = VNFI(vnfID=VNF_TYPE_FORWARD, vnfType=VNF_TYPE_FORWARD,
                vnfiID=uuid.uuid1(), node=server)
            vnfiSequence[index].append(vnfi)

            server = Server("ens3",SFF2_DATAPATH_IP, SERVER_TYPE_NFVI)
            server.setServerID(SFF2_SERVERID)
            server.setControlNICIP(SFF2_CONTROLNIC_IP)
            server.setControlNICMAC(SFF2_CONTROLNIC_MAC)
            server.setDataPathNICMAC(SFF2_DATAPATH_MAC)
            vnfi = VNFI(vnfID=VNF_TYPE_FORWARD, vnfType=VNF_TYPE_FORWARD,
                vnfiID=uuid.uuid1(), node=server)
            vnfiSequence[index].append(vnfi)

        return vnfiSequence

    def genUniDirection10BackupForwardingPathSet(self):
        primaryForwardingPath = {1:[[(0,10001),(0,1),(0,2),(0,10002)],[(1,10002),(1,2),(1,1),(1,10001)]]}
        mappingType = MAPPING_TYPE_UFRR
        backupForwardingPath = {
            1:{
                (("failureNodeID", 2), ("repairMethod", "fast-reroute"), ("repairSwitchID", 1), ("newPathID", 2)):
                    [[(0,1),(0,3),(0,2),(0,10003)],[(1,10003),(1,2),(1,3),(1,1),(1,10001)]]
            }
        }
        return ForwardingPathSet(primaryForwardingPath,mappingType,
            backupForwardingPath)

    def genUniDirection11BackupForwardingPathSet(self):
        primaryForwardingPath = {1:[[(0,10001),(0,1),(0,2),(0,10002)],[(1,10002),(1,2),(1,1),(1,10001)]]}
        mappingType = MAPPING_TYPE_UFRR
        backupForwardingPath = {
            1:{
                (("failureNodeID", 2), ("repairMethod", "fast-reroute"), ("repairSwitchID", 1), ("newPathID", 2)):
                    [[(0,1),(0,3),(0,10003)],[(1,10003),(1,3),(1,1),(1,10001)]],
                (("failureNodeID", 10002), ("repairMethod", "fast-reroute"), ("repairSwitchID", 2), ("newPathID", 3)):
                    [[(0,2),(0,3),(0,10003)],[(1,10003),(1,3),(1,1),(1,10001)]]
            }
        }
        return ForwardingPathSet(primaryForwardingPath,mappingType,
            backupForwardingPath)

    def genBiDirection10BackupForwardingPathSet(self):
        primaryForwardingPath = {
            1: [[(0, 10001), (0, 1), (0, 2), (0, 10002)], [(1, 10002), (1, 2), (1, 1), (1, 10001)]],
            128: [[(0, 10001), (0, 1), (0, 2), (0, 10002)], [(1, 10002), (1, 2), (1, 1), (1, 10001)]]
        }
        mappingType = MAPPING_TYPE_UFRR
        backupForwardingPath = {
            1:{
                (("failureNodeID", 2), ("repairMethod", "fast-reroute"), ("repairSwitchID", 1), ("newPathID", 2)):
                    [[(0,1),(0,3),(0,2),(0,10002)],[(1,10002),(1,2),(1,3),(1,1),(1,10001)]]
            },
            128:{
                (("failureNodeID", 2), ("repairMethod", "fast-reroute"), ("repairSwitchID", 1), ("newPathID", 129)):
                    [[(0,1),(0,3),(0,2),(0,10002)],[(1,10002),(1,2),(1,3),(1,1),(1,10001)]]
            }
        }
        return ForwardingPathSet(primaryForwardingPath,mappingType,
            backupForwardingPath)

    def genUniDirection12BackupSFCI(self):
        vnfiSequence = self.gen12BackupVNFISequence()
        return SFCI(self.assignSFCIID(),vnfiSequence, None,
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

    def genUniDirection12BackupForwardingPathSet(self):
        primaryForwardingPath = {1:[[(0,10001),(0,1),(0,2),(0,10003)],[(1,10003),(1,2),(1,1),(1,10001)]]}
        mappingType = MAPPING_TYPE_UFRR
        backupForwardingPath = {
            1:{
                (("failureNodeID", 2), ("repairMethod", "fast-reroute"), ("repairSwitchID", 1), ("newPathID", 2)):
                    [[(0,1),(0,3),(0,10005)],[(1,10005),(1,3),(1,1),(1,10001)]],
                (("failureNodeID", 10003), ("repairMethod", "fast-reroute"), ("repairSwitchID", 2), ("newPathID", 3)):
                    [[(0,2),(0,10004)],[(1,10004),(1,2),(1,1),(1,10001)]]
            }
        }
        return ForwardingPathSet(primaryForwardingPath,mappingType,
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
        self.sP.runShellCommand("python " + clearAllSAMQueue.__file__)

    def cleanLog(self):
        self.sP.runShellCommand("python " + cleanAllLogFile.__file__)

    def killAllModule(self):
        self.sP.runShellCommand("sudo python " + killAllSAMPythonScripts.__file__)

    def genSwitchList(self, num, switchType, 
            switchLANNetlist, switchIDList, supportVNFList=None):
        switches = []
        for i in range(num):
            switch = Switch(switchIDList[i], switchType, switchLANNetlist[i])
            if type(supportVNFList) == list:
                switch.supportVNF = supportVNFList[i]
            switches.append(switch)
        return switches

    def genServerList(self, num, serverType, serverCIPList,
            serverDPIPList, serverIDList):
        servers = []
        for i in range(num):
            server = Server("ens3",serverDPIPList[i], serverType)
            server.setServerID(serverIDList[i])
            server.setControlNICIP([serverCIPList[i]])
            server.setControlNICMAC(self.genRandomMacAddress())
            for vnfType in range(VNF_TYPE_MAX+1):
                server.addVNFSupport(vnfType)
            server.updateResource()
            servers.append(server)
        return servers

    def genRandomMacAddress(self):
        return "02:00:00:%02x:%02x:%02x" % (random.randint(0, 255),
            random.randint(0, 255), random.randint(0, 255))

    def genAddSFCRequest(self, sfc):
        sfc.backupInstanceNumber = 3
        request = Request(0, uuid.uuid1(), REQUEST_TYPE_ADD_SFC,
            REQUEST_PROCESSOR_QUEUE, REQUEST_STATE_INITIAL, {'sfc':sfc,
                'zone':"", 'mappingType':MAPPING_TYPE_E2EP})
        return request

    def genAddSFCIRequest(self, sfc, sfci):
        sfc.backupInstanceNumber = 3
        request = Request(0, uuid.uuid1(), REQUEST_TYPE_ADD_SFCI,
            REQUEST_PROCESSOR_QUEUE, REQUEST_STATE_INITIAL, {'sfc':sfc,
                'sfci':sfci, 'zone':"", 'mappingType':MAPPING_TYPE_E2EP})
        return request

    def genDelSFCRequest(self, sfc):
        request = Request(0, uuid.uuid1(), REQUEST_TYPE_DEL_SFC,
            REQUEST_PROCESSOR_QUEUE, REQUEST_STATE_INITIAL, {'sfc':sfc,
                'zone':""})
        return request

    def genDelSFCIRequest(self, sfc, sfci):
        request = Request(0, uuid.uuid1(), REQUEST_TYPE_DEL_SFCI,
            REQUEST_PROCESSOR_QUEUE, REQUEST_STATE_INITIAL, {'sfc':sfc,
                'sfci':sfci, 'zone':""})
        return request

    def _genSFCIID(self):
        TestBase.sfciCounter = TestBase.sfciCounter + 1
        return TestBase.sfciCounter
