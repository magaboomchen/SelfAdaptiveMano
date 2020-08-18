from sam.base.sfc import *
from sam.base.vnf import *
from sam.base.server import *
from sam.base.path import *
from sam.serverController.classifierController import *
from sam.serverAgent.serverAgent import ServerAgent
from sam.serverController.serverManager.serverManager import *
from sam.base.command import *
from sam.base.socketConverter import *
from sam.base.shellProcessor import ShellProcessor
from sam.test.fixtures.mediatorStub import *
from sam.test.fixtures.orchestrationStub import *
import uuid
import subprocess
import psutil
import pytest
import time
from scapy.all import *

OUTTER_CLIENT_IP = "1.1.1.1"
WEBSITE_REAL_IP = "2.2.0.34"

CLASSIFIER_DATAPATH_IP = "2.2.0.35"
CLASSIFIER_DATAPATH_MAC = "52:54:00:05:4D:7D"
CLASSIFIER_CONTROL_IP = "192.168.122.34"

VNFI1_0_IP = "10.0.17.1"
VNFI1_1_IP = "10.0.17.128"

SFF1_DATAPATH_IP = "2.2.0.69"
SFF1_DATAPATH_MAC = "52:54:00:9D:F4:F4"
SFF1_CONTROLNIC_IP = "192.168.122.134"
SFF1_CONTROLNIC_MAC = "52:54:00:80:ea:94"

SFF2_DATAPATH_IP = "2.2.0.99"
SFF2_DATAPATH_MAC = "52:54:00:F7:34:25"
SFF2_CONTROLNIC_IP = "192.168.122.208"
SFF2_CONTROLNIC_MAC = "52:54:00:D5:A7:0C"

class TestBase(object):
    MAXSFCIID = 0

    def assignSFCIID(self):
        TestBase.MAXSFCIID = TestBase.MAXSFCIID + 1
        return TestBase.MAXSFCIID

    def genClassifier(self, datapathIfIP):
        classifier = Server("ens3", datapathIfIP, SERVER_TYPE_CLASSIFIER)
        classifier.setServerID(uuid.uuid1())
        classifier._serverDatapathNICIP = CLASSIFIER_DATAPATH_IP
        classifier._ifSet["ens3"] = {}
        classifier._ifSet["ens3"]["IP"] = CLASSIFIER_CONTROL_IP
        classifier._serverDatapathNICMAC = CLASSIFIER_DATAPATH_MAC
        return classifier

    def genTesterServer(self,datapathIfIP,datapathIfMac):
        server = Server("virbr0", datapathIfIP, SERVER_TYPE_TESTER)
        server.setServerID(uuid.uuid1())
        server.updateControlNICMAC()
        server.updateIfSet()
        server._serverDatapathNICMAC = datapathIfMac
        return server

    def genUniDirectionSFC(self,classifier):
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
            backupInstanceNumber, applicationType, directions)

    def genBiDirectionSFC(self,classifier):
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
            backupInstanceNumber, applicationType, directions)

    def genUniDirection10BackupSFCI(self):
        VNFISequence = self.gen10BackupVNFISequence()
        return SFCI(self.assignSFCIID(),VNFISequence, None,
            self.genUniDirection10BackupForwardingPathSet())

    def genBiDirection10BackupSFCI(self):
        VNFISequence = self.gen10BackupVNFISequence()
        return SFCI(self.assignSFCIID(),VNFISequence, None,
            self.genBiDirection10BackupForwardingPathSet())

    def genUniDirection11BackupSFCI(self):
        VNFISequence = self.gen11BackupVNFISequence()
        return SFCI(self.assignSFCIID(),VNFISequence, None,
            self.genUniDirection11BackupForwardingPathSet())

    def gen10BackupVNFISequence(self,SFCLength=1):
        # hard-code function
        VNFISequence = []
        for index in range(SFCLength):
            VNFISequence.append([])
            for iN in range(1):
                server = Server("ens3",SFF1_DATAPATH_IP,SERVER_TYPE_NORMAL)
                server.setServerID(SERVERID_OFFSET + index)
                server.setControlNICIP(SFF1_CONTROLNIC_IP)
                server.setControlNICMAC(SFF1_CONTROLNIC_MAC)
                server.setDataPathNICMAC(SFF1_DATAPATH_MAC)
                vnfi = VNFI(VNF_TYPE_FORWARD,VNFType=VNF_TYPE_FORWARD,VNFIID=uuid.uuid1(),
                    node=server)
                VNFISequence[index].append(vnfi)
        return VNFISequence

    def gen11BackupVNFISequence(self,SFCLength=1):
        # hard-code function
        VNFISequence = []
        for index in range(SFCLength):
            VNFISequence.append([])
            
            server = Server("ens3",SFF1_DATAPATH_IP,SERVER_TYPE_NORMAL)
            server.setServerID(SERVERID_OFFSET + 1)
            server.setControlNICIP(SFF1_CONTROLNIC_IP)
            server.setControlNICMAC(SFF1_CONTROLNIC_MAC)
            server.setDataPathNICMAC(SFF1_DATAPATH_MAC)
            vnfi = VNFI(VNF_TYPE_FORWARD,VNFType=VNF_TYPE_FORWARD,VNFIID=uuid.uuid1(),
                node=server)
            VNFISequence[index].append(vnfi)

            server = Server("ens3",SFF2_DATAPATH_IP,SERVER_TYPE_NORMAL)
            server.setServerID(SERVERID_OFFSET + 2)
            server.setControlNICIP(SFF2_CONTROLNIC_IP)
            server.setControlNICMAC(SFF2_CONTROLNIC_MAC)
            server.setDataPathNICMAC(SFF2_DATAPATH_MAC)
            vnfi = VNFI(VNF_TYPE_FORWARD,VNFType=VNF_TYPE_FORWARD,VNFIID=uuid.uuid1(),
                node=server)
            VNFISequence[index].append(vnfi)

        return VNFISequence

    def genUniDirection10BackupForwardingPathSet(self):
        primaryForwardingPath = {1:[10001,1,2,10002],
            128:[10002,2,1,10001]}
        frrType = "UFFR"
        # {(srcID,dstID,pathID):forwardingPath}
        backupForwardingPath = {(1,2,2):[[1,3,2,10002],[10002,2,3,1,10001]]}
        return ForwardingPathSet(primaryForwardingPath,frrType,
            backupForwardingPath)

    def genUniDirection11BackupForwardingPathSet(self):
        primaryForwardingPath = {1:[10001,1,2,10002],
            128:[10002,2,1,10001]}
        frrType = "UFFR"
        # {(srcID,dstID,pathID):forwardingPath}
        backupForwardingPath = {(1,2,2):[[1,3,10003],[10003,3,1,10001]],
            (2,10002,3):[[2,3,10003],[10003,3,1,10001]]}
        return ForwardingPathSet(primaryForwardingPath,frrType,
            backupForwardingPath)

    def genBiDirection10BackupForwardingPathSet(self):
        # TODO: bi-direction
        pass
        return None

    def recvCmd(self,queue):
        self._messageAgent = MessageAgent()
        self._messageAgent.startRecvMsg(queue)
        print("testBase:recvCmd")
        while True:
            msg = self._messageAgent.getMsg(queue)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            else:
                body = msg.getbody()
                if self._messageAgent.isCommand(body):
                    return body
                else:
                    logging.error("Unknown massage body")

    def recvCmdRply(self,queue):
        self._messageAgent = MessageAgent()
        self._messageAgent.startRecvMsg(queue)
        while True:
            msg = self._messageAgent.getMsg(queue)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            else:
                body = msg.getbody()
                if self._messageAgent.isCommandReply(body):
                    print("testBase:recvCmdRply")
                    return body
                else:
                    logging.error("Unknown massage body")

    def sendCmd(self,queue,msgType,cmd):
        self._messageAgent = MessageAgent()
        msg = SAMMessage(msgType, cmd)
        self._messageAgent.sendMsg(queue,msg)