#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid
import random
import logging

from sam.base.acl import ACL_ACTION_ALLOW, ACL_PROTO_UDP, ACLTuple
from sam.base.sfc import SFC, SFCI, APP_TYPE_NORTHSOUTH_WEBSITE
from sam.base.vnf import PREFERRED_DEVICE_TYPE_SERVER, VNF, VNFI, VNF_TYPE_FORWARD, VNF_TYPE_MAX, VNFI_RESOURCE_QUOTA_SMALL
from sam.base.slo import SLO
from sam.base.server import Server, SERVER_TYPE_CLASSIFIER, SERVER_TYPE_NFVI, \
    SERVER_TYPE_TESTER
from sam.base.path import ForwardingPathSet, MAPPING_TYPE_UFRR, MAPPING_TYPE_E2EP
from sam.base.switch import Switch
from sam.base.request import Request, REQUEST_TYPE_ADD_SFC, REQUEST_TYPE_ADD_SFCI, \
    REQUEST_STATE_INITIAL, REQUEST_TYPE_DEL_SFC, REQUEST_TYPE_DEL_SFCI
from sam.base.messageAgent import DEFAULT_ZONE, SIMULATOR_ZONE, TURBONET_ZONE, SAMMessage, MessageAgent, MSG_TYPE_REQUEST, \
    REQUEST_PROCESSOR_QUEUE
from sam.base.routingMorphic import IPV4_ROUTE_PROTOCOL, IPV6_ROUTE_PROTOCOL, ROCEV1_ROUTE_PROTOCOL, SRV6_ROUTE_PROTOCOL, RoutingMorphic
from sam.base.test.fixtures.ipv4MorphicDict import ipv4MorphicDictTemplate
from sam.dashboard.dashboardInfoBaseMaintainer import DashboardInfoBaseMaintainer
from sam.measurement.mConfig import SIMULATOR_ZONE_ONLY
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer
from sam.regulator import regulator
from sam.toolkit.cleanAllLogFile import cleanAllLogFile
from sam.toolkit.clearAllSAMQueue import clearAllSAMQueue
from sam.toolkit.killAllSAMPythonScripts import killAllSAMPythonScripts
from sam.serverController.serverManager import serverManager
from sam.serverController.classifierController import classifierControllerCommandAgent
from sam.serverController.sffController import sffControllerCommandAgent
from sam.serverController.vnfController import vnfController
from sam.orchestration import orchestrator
from sam.mediator import mediator
from sam.measurement import measurer

DCN_GATEWAY_IP = "2.2.0.0"

OUTTER_CLIENT_IP = "1.1.1.1"
OUTTER_CLIENT_IPV6 = "3ff2:1ce1:2::"
WEBSITE_REAL_IP = "3.3.3.3"
WEBSITE_REAL_IPV6 = "3ff3:1ce1:2::"
APP1_REAL_IP = "4.4.4.4"
APP2_REAL_IP = "5.5.5.5"
APP3_REAL_IP = "6.6.6.6"
APP4_REAL_IP = "7.7.7.7"
APP5_REAL_IP = "8.8.8.8"

TEST_SERVERID = 19999

TESTER_SERVER_DATAPATH_IP = "192.168.123.1"
TESTER_SERVER_DATAPATH_MAC = "fe:54:00:05:4d:7d"
TESTER_SERVER_INTF = "ens5f1"

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
RL_VNFI1_0_IP = "10.96.1.1"
RL_VNFI1_1_IP = "10.96.1.128"
NAT_VNFI1_0_IP = "10.112.1.1"
NAT_VNFI1_1_IP = "10.112.1.128"
VPN_VNFI1_0_IP = "10.128.1.1"
VPN_VNFI1_1_IP = "10.128.1.128"
SFCI1_0_EGRESS_IP = "10.0.1.1"
SFCI1_1_EGRESS_IP = "10.0.1.128"


# SFF1_DATAPATH_IP = "2.2.0.69"
# SFF1_DATAPATH_MAC = "52:54:00:ad:18:c2"
# SFF1_CONTROLNIC_IP = "192.168.122.134"
# SFF1_CONTROLNIC_MAC = "52:54:00:80:ea:94"
# SFF1_SERVERID = 10003

SFF1_CONTROLNIC_INTERFACE = "enp1s0"
SFF1_DATAPATH_IP = "2.2.0.98"
SFF1_DATAPATH_MAC = "52:67:f7:65:01:00"
SFF1_CONTROLNIC_IP = "192.168.20.6"
SFF1_CONTROLNIC_MAC = "52:54:00:9d:c2:77"
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

DIRECTION0_TRAFFIC_SPI = 1
DIRECTION0_TRAFFIC_SI = 1
DIRECTION1_TRAFFIC_SPI = 0x800001
DIRECTION1_TRAFFIC_SI = 1

logging.basicConfig(level=logging.INFO)


class TestBase(object):
    MAXSFCIID = 0
    sfciCounter = 0
    logging.getLogger("pika").setLevel(logging.WARNING)

    def resetRabbitMQConf(self, filePath, serverIP,
            serverUser, serverPasswd):
        with open(filePath, 'w') as f:
            f.write("{\n")
            f.write("    RABBITMQSERVERIP = '{0}'\n".format(serverIP))
            f.write("    RABBITMQSERVERUSER = '{0}'\n".format(serverUser))
            f.write("    RABBITMQSERVERPASSWD = '{0}'\n".format(serverPasswd))
            f.write("}\n")

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

    def runRegulator(self):
        filePath = regulator.__file__
        self.sP.runPythonScript(filePath)

    def genUniDirectionSFC(self, classifier, zone=DEFAULT_ZONE):
        sfcUUID = uuid.uuid1()
        vNFTypeSequence = [VNF_TYPE_FORWARD]
        vnfSequence = [VNF(uuid.uuid1(), VNF_TYPE_FORWARD,
                            None, PREFERRED_DEVICE_TYPE_SERVER)]
        maxScalingInstanceNumber = 1
        backupInstanceNumber = 0
        applicationType = APP_TYPE_NORTHSOUTH_WEBSITE
        direction1 = {
            'ID': 0,
            'source': {"IPv4":"*", "node": None},
            'ingress': classifier,
            'match': {'srcIP': "*",'dstIP':WEBSITE_REAL_IP,
                'srcPort': "*",'dstPort': "*",'proto': "*"},
            'egress': classifier,
            'destination': {"IPv4":WEBSITE_REAL_IP, "node": None}
        }
        directions = [direction1]
        slo = SLO(latency=35, throughput=10)
        return SFC(sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
            backupInstanceNumber, applicationType, directions,
            {'zone':zone}, slo=slo, vnfSequence=vnfSequence,
            vnfiResourceQuota=VNFI_RESOURCE_QUOTA_SMALL)

    def genBiDirectionSFC(self, classifier, vnfTypeSeq=None,
                            routingMorphicTemplate=ipv4MorphicDictTemplate,
                            zone=DEFAULT_ZONE):
        sfcUUID = uuid.uuid1()
        if vnfTypeSeq == None:
            vNFTypeSequence = [VNF_TYPE_FORWARD]
        else:
            vNFTypeSequence = vnfTypeSeq
        vnfSequence = []
        for idx in range(len(vnfTypeSeq)):
            vnf = VNF(uuid.uuid1(), vNFTypeSequence[idx],
                        None, PREFERRED_DEVICE_TYPE_SERVER)
            vnfSequence.append(vnf)
        maxScalingInstanceNumber = 1
        backupInstanceNumber = 0
        applicationType = APP_TYPE_NORTHSOUTH_WEBSITE
        direction1 = {
            'ID': 0,
            'source': {"IPv4":"*", "node": None},
            'ingress': classifier,
            'match': {'srcIP': "*",'dstIP': WEBSITE_REAL_IP,
                'srcPort': "*",'dstPort': "*",'proto': "*"},
            'egress': classifier,
            'destination': {"IPv4": WEBSITE_REAL_IP, "node": None}
        }
        direction2 = {
            'ID': 1,
            'source': {"IPv4": WEBSITE_REAL_IP, "node": None},
            'ingress': classifier,
            'match': {'srcIP': WEBSITE_REAL_IP,'dstIP': "*",
                'srcPort': "*",'dstPort': "*",'proto': "*"},
            'egress': classifier,
            'destination': {"IPv4":"*", "node": None}
        }
        directions = [direction1, direction2]
        routingMorphic = RoutingMorphic()
        routingMorphic.from_dict(routingMorphicTemplate)
        slo = SLO(latency=35, throughput=10)
        return SFC(sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
            backupInstanceNumber, applicationType, directions=directions,
            attributes={'zone':zone},
            routingMorphic=routingMorphic,
            vnfSequence=vnfSequence, slo=slo,
            vnfiResourceQuota=VNFI_RESOURCE_QUOTA_SMALL
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
        # primaryForwardingPath = {
        #     1:[[10001,1,2,10002],[10002,2,1,10001]],
        #     128:[[10001,1,2,10002],[10002,2,1,10001]]
        # }
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
        tmpMessageAgent = MessageAgent()
        tmpMessageAgent.startRecvMsg(queue)
        logging.info("testBase:recvCmd")
        try:
            while True:
                msg = tmpMessageAgent.getMsg(queue)
                msgType = msg.getMessageType()
                if msgType == None:
                    pass
                else:
                    body = msg.getbody()
                    if tmpMessageAgent.isCommand(body):
                        return body
                    else:
                        logging.error("Unknown massage body: {0}".format(
                            type(body)))
        finally:
           del tmpMessageAgent

    def recvCmdRply(self, queue):
        tmpMessageAgent = MessageAgent()
        tmpMessageAgent.startRecvMsg(queue)
        while True:
            msg = tmpMessageAgent.getMsg(queue)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            else:
                body = msg.getbody()
                if tmpMessageAgent.isCommandReply(body):
                    logging.info("testBase:recvCmdRply")
                    return body
                else:
                    logging.error("Unknown massage body")

    def startMsgAgentRPCReciever(self, ip, port):
        self.tmpMessageAgent = MessageAgent()
        self.tmpMessageAgent.startMsgReceiverRPCServer(ip, port)

    def recvCmdRplyByRPC(self, ip, port):
        while True:
            msg = self.tmpMessageAgent.getMsg("{0}:{1}".format(ip, port))
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            else:
                body = msg.getbody()
                if self.tmpMessageAgent.isCommandReply(body):
                    logging.info("testBase:recvCmdRply")
                    return body
                else:
                    logging.error("Unknown massage body")

    def sendCmd(self, queue, msgType, cmd):
        tmpMessageAgent = MessageAgent()
        msg = SAMMessage(msgType, cmd)
        tmpMessageAgent.sendMsg(queue, msg)
        del tmpMessageAgent

    def sendCmdByRPC(self, dstIP, dstPort, msgType, cmd):
        tmpMessageAgent = MessageAgent()
        oSP = tmpMessageAgent.getOpenSocketPort()
        tmpMessageAgent.startMsgReceiverRPCServer("localhost", oSP)
        msg = SAMMessage(msgType, cmd)
        tmpMessageAgent.sendMsgByRPC(dstIP, dstPort, msg)
        del tmpMessageAgent

    def sendCmdRply(self, queue, msgType, cmdRply):
        tmpMessageAgent = MessageAgent()
        msg = SAMMessage(msgType, cmdRply)
        tmpMessageAgent.sendMsg(queue, msg)
        del tmpMessageAgent

    def sendRequest(self, queue, request):
        tmpMessageAgent = MessageAgent()
        msg = SAMMessage(MSG_TYPE_REQUEST, request)
        tmpMessageAgent.sendMsg(queue, msg)
        del tmpMessageAgent

    def sendRequestByGRPC(self, dstIP, dstPort, request):
        tmpMessageAgent = MessageAgent()
        oSP = tmpMessageAgent.getOpenSocketPort()
        tmpMessageAgent.startMsgReceiverRPCServer("localhost", oSP)
        msg = SAMMessage(MSG_TYPE_REQUEST, request)
        tmpMessageAgent.sendMsgByRPC(dstIP, dstPort, msg)
        return tmpMessageAgent

    def recvRequest(self, queue):
        tmpMessageAgent = MessageAgent()
        tmpMessageAgent.startRecvMsg(queue)
        try:
            while True:
                msg = tmpMessageAgent.getMsg(queue)
                msgType = msg.getMessageType()
                if msgType == None:
                    pass
                else:
                    body = msg.getbody()
                    if tmpMessageAgent.isRequest(body):
                        logging.info("testBase: recv a request")
                        return body
                    else:
                        logging.error("Unknown massage body")
        finally:
            del tmpMessageAgent

    def recvReply(self, queue):
        tmpMessageAgent = MessageAgent()
        tmpMessageAgent.startRecvMsg(queue)
        try:
            while True:
                msg = tmpMessageAgent.getMsg(queue)
                msgType = msg.getMessageType()
                if msgType == None:
                    pass
                else:
                    body = msg.getbody()
                    if tmpMessageAgent.isReply(body):
                        logging.info("testBase: recv a reply")
                        return body
                    else:
                        logging.error("Unknown massage body")
        finally:
            del tmpMessageAgent

    def recvReplyByRPC(self, listenIP, listenPort):
        tmpMessageAgent = MessageAgent()
        tmpMessageAgent.startMsgReceiverRPCServer(listenIP, listenPort)
        try:
            while True:
                msg = tmpMessageAgent.getMsgByRPC(listenIP, listenPort)
                msgType = msg.getMessageType()
                if msgType == None:
                    pass
                else:
                    body = msg.getbody()
                    if tmpMessageAgent.isReply(body):
                        logging.info("testBase: recv a reply")
                        return body
                    else:
                        logging.error("Unknown massage body")
        finally:
            del tmpMessageAgent

    def clearQueue(self):
        clearAllSAMQueue()

    def cleanLog(self):
        cleanAllLogFile()

    def killAllModule(self):
        killAllSAMPythonScripts()

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
            REQUEST_PROCESSOR_QUEUE, requestState=REQUEST_STATE_INITIAL,
                attributes={'sfc':sfc,
                    'zone':DEFAULT_ZONE, 'mappingType':MAPPING_TYPE_E2EP})
        return request

    def genAddSFCIRequest(self, sfc, sfci):
        sfc.backupInstanceNumber = 3
        request = Request(0, uuid.uuid1(), REQUEST_TYPE_ADD_SFCI,
            REQUEST_PROCESSOR_QUEUE, requestState=REQUEST_STATE_INITIAL,
                attributes={'sfc':sfc,
                    'sfci':sfci, 'zone':DEFAULT_ZONE, 'mappingType':MAPPING_TYPE_E2EP})
        return request

    def genDelSFCRequest(self, sfc):
        request = Request(0, uuid.uuid1(), REQUEST_TYPE_DEL_SFC,
            REQUEST_PROCESSOR_QUEUE, requestState=REQUEST_STATE_INITIAL,
                attributes={'sfc':sfc, 'zone':DEFAULT_ZONE})
        return request

    def genDelSFCIRequest(self, sfc, sfci):
        request = Request(0, uuid.uuid1(), REQUEST_TYPE_DEL_SFCI,
            REQUEST_PROCESSOR_QUEUE, requestState=REQUEST_STATE_INITIAL,
                attributes={'sfc':sfc, 'sfci':sfci, 'zone':DEFAULT_ZONE})
        return request

    def _genSFCIID(self):
        TestBase.sfciCounter = TestBase.sfciCounter + 1
        return TestBase.sfciCounter

    def initZone(self):
        self._dashib = DashboardInfoBaseMaintainer("localhost", "dbAgent",
            "123", reInitialTable=True)
        self._dashib.addZone(SIMULATOR_ZONE)
        if not SIMULATOR_ZONE_ONLY:
            self._dashib.addZone(TURBONET_ZONE)

    def genFWConfigExample(self, routingMorphic):
        fwConfigList = []
        if routingMorphic == IPV4_ROUTE_PROTOCOL:
            dstAddr="3.3.3.3"
        elif routingMorphic == IPV6_ROUTE_PROTOCOL:
            dstAddr="2026:0000::"
        elif routingMorphic == SRV6_ROUTE_PROTOCOL:
            dstAddr="2026:0000::"
        elif routingMorphic == ROCEV1_ROUTE_PROTOCOL:
            dstAddr="2026:0000::"
        else:
            dstAddr="3.3.3.3"
        entry = ACLTuple(ACL_ACTION_ALLOW, ACL_PROTO_UDP, dstAddr=dstAddr)
        fwConfigList.append(entry)
        return fwConfigList

    def dropRequestAndSFCAndSFCITableInDB(self):
        _oib = OrchInfoBaseMaintainer("localhost", "dbAgent", "123",
                                            True)
        _oib.dropTable()                                           
        del _oib
    
    def cleanRequestAndSFCAndSFCITableInDB(self):
        _oib = OrchInfoBaseMaintainer("localhost", "dbAgent", "123",
                                            True)
        del _oib