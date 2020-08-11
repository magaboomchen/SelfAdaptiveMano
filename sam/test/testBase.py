from sam.base.sfc import *
from sam.base.vnf import *
from sam.base.server import *
from sam.serverController.classifierController import *
from sam.serverAgent.serverAgent import ServerAgent
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

VNFI1_IP = "10.0.18.1"
WEBSITE_REAL_IP = "2.2.2.2"
CLASSIFIER_DATAPATH_IP = "2.2.0.35"
CLASSIFIER_DATAPATH_MAC = "52:54:00:05:4D:7D"
CLASSIFIER_CONTROL_IP = "192.168.122.34"

OUTTER_CLIENT_IP = "1.1.1.1"

TESTER_SERVER_DATAPATH_IP = "192.168.123.1"
TESTER_SERVER_DATAPATH_MAC = "fe:54:00:05:4d:7d"

class TestBase(object):
    MAXSFCIID = 0

    def assignSFCIID(self):
        TestBase.MAXSFCIID = TestBase.MAXSFCIID + 1
        return TestBase.MAXSFCIID

    def genClassifier(self, datapathIfIP):
        classifier = Server("ens3", datapathIfIP, SERVER_TYPE_CLASSIFIER)
        classifier.updateServerID(uuid.uuid1())
        classifier._ifSet["ens3"] = {}
        classifier._ifSet["ens3"]["IP"] = CLASSIFIER_CONTROL_IP
        classifier._serverDatapathNICMAC = CLASSIFIER_DATAPATH_MAC
        return classifier

    def genTesterServer(self):
        server = Server("virbr0", "192.168.123.1", SERVER_TYPE_TESTER)
        server.updateServerID(uuid.uuid1())
        server.updateControlNICMAC()
        server.updateIfSet()
        server._serverDatapathNICMAC = "fe:54:00:05:4d:7d"
        return server

    def genSFC(self,classifier):
        sfcUUID = uuid.uuid1()
        vNFTypeSequence = [VNF_TYPE_FW]
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
            'destination': WEBSITE_REAL_IP
        }
        direction2 = {
            'ID': 1,
            'source': WEBSITE_REAL_IP,
            'ingress': classifier,
            'match': {'srcIP': WEBSITE_REAL_IP,'dstIP':None,
                'srcPort': None,'dstPort': None,'proto': None},
            'egress': classifier,
            'destination': None
        }
        directions = [direction1,direction2]
        return SFC(sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
            backupInstanceNumber, applicationType, directions)

    def genSFCI(self):
        VNFISequence = self.genVNFISequence()
        return SFCI(self.assignSFCIID(),VNFISequence)

    def genVNFISequence(self,SFCLength=1):
        VNFISequence = []
        for index in range(SFCLength):
            server = Server("ens3",VNFI1_IP,SERVER_TYPE_NORMAL)
            vnfi = VNFI(uuid.uuid1(),VNFType=VNF_TYPE_FW,VNFIID=VNF_TYPE_FW,
                node=server)
            VNFISequence.append(vnfi)
        return VNFISequence

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
        print("testBase:recvCmdRply")
        while True:
            msg = self._messageAgent.getMsg(queue)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            else:
                body = msg.getbody()
                if self._messageAgent.isCommandReply(body):
                    return body
                else:
                    logging.error("Unknown massage body")

    def sendCmd(self,queue,msgType,cmd):
        self._messageAgent = MessageAgent()
        msg = SAMMessage(msgType, cmd)
        self._messageAgent.sendMsg(queue,msg)