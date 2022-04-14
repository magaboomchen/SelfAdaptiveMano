#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging
from scapy.all import *
import time

import pytest

from sam.base.acl import *
from sam.base import server
from sam.base.sfc import *
from sam.base.vnf import *
from sam.base.server import *
from sam.base.command import *
from sam.base.pickleIO import PickleIO
from sam.base.socketConverter import SocketConverter, BCAST_MAC
from sam.base.shellProcessor import ShellProcessor
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.test.fixtures.vnfControllerStub import *
from sam.test.testBase import *
from sam.serverController.classifierController import ClassifierControllerCommandAgent

MANUAL_TEST = True
TESTER_SERVER_DATAPATH_IP = "2.2.0.36"
TESTER_SERVER_DATAPATH_MAC = "00:1b:21:c0:8f:ae"

SFF0_DATAPATH_IP = "2.2.0.38"
SFF0_DATAPATH_MAC = "00:1b:21:c0:8f:98"
SFF0_CONTROLNIC_IP = "192.168.0.173"
SFF0_CONTROLNIC_MAC = "18:66:da:85:1c:c3"

# May be BESS doesn't support NUMA architecture!
MAX_SFCI = 5

logging.basicConfig(level=logging.INFO)
logging.getLogger("pika").setLevel(logging.WARNING)


class TestVNFSFCIAdderClass(TestBase):
    def __init__(self):
        logConf = LoggerConfigurator(__name__, './log', 'TestVNFSFCIAdderClass.log',
            level='debug')
        self.logger = logConf.getLogger()
        self.logger.info('Initialize vnf controller.')

    def measure(self):
        # setup
        self.sP = ShellProcessor()
        self.clearQueue()
        self.killAllModule()

        self.mediatorRcvAgent = MessageAgent()
        self.mediatorRcvAgent.startRecvMsg(MEDIATOR_QUEUE)

        self.msgSendAgent = MessageAgent()

        classifier = None
        self.mediator = MediatorStub()
        self.sfc = self.genBiDirectionSFC(classifier)

        self.genSFCIList()
        self.genAddSFCICmdList()

        self.deployTimeDict = {}
        self.sendCmdTimeDict = {}
        # for sfciNum in range(1,6):
        for sfciNum in range(1,2):
            self.deployTimeDict[sfciNum] = []
            self.sendCmdTimeDict[sfciNum] = []
            # for expNum in range(10):
            for expNum in range(0):
                deployTime, sendCmdTime = self.startAnExp(sfciNum)
                self.deployTimeDict[sfciNum].append(deployTime)
                self.sendCmdTimeDict[sfciNum].append(sendCmdTime)

        self.pIO = PickleIO()
        self.pIO.writePickleFile("./deployTimeRes.pickle", self.deployTimeDict)
        self.logger.info("deploy time dict: {0}".format(self.deployTimeDict))

        self.pIO.writePickleFile("./sendCmdTimeRes.pickle", self.sendCmdTimeDict)
        self.logger.info("send cmd time dict: {0}".format(self.sendCmdTimeDict))

    def startAnExp(self, sfciNum):
        self.runSFFController()
        self.runVNFController()
        self.waitingCmdDict = {}
        startTime = time.time()
        self.addSFCI2SFF(sfciNum)
        self.addVNFI2Server(sfciNum)
        medTime = time.time()
        sendCmdTime = medTime - startTime
        self.recvAllCmdReplys()
        endTime = time.time()
        deployTime = endTime - startTime
        # self.logger.info("Please input to continue")
        # input()
        self.delVNFI4Server(sfciNum)
        self.killSFFController()
        self.killVNFController()
        return deployTime, sendCmdTime

    def sendCmd(self, queue, msgType, cmd):
        msg = SAMMessage(msgType, cmd)
        self.msgSendAgent.sendMsg(queue, msg)

    def addSFCI2SFF(self, sfciNum=MAX_SFCI):
        logging.info("setup add SFCI to sff")
        for sfciIndex in range(sfciNum):
            addSFCICmd = self.addSFCICmdList[sfciIndex]
            addSFCICmd.cmdID = uuid.uuid1()
            self.waitingCmdDict[addSFCICmd.cmdID] = 1
            self.sendCmd(SFF_CONTROLLER_QUEUE,
                MSG_TYPE_SFF_CONTROLLER_CMD, addSFCICmd)

    def addVNFI2Server(self, sfciNum=MAX_SFCI):
        for sfciIndex in range(sfciNum):
            addSFCICmd = self.addSFCICmdList[sfciIndex]
            addSFCICmd.cmdID = uuid.uuid1()
            self.waitingCmdDict[addSFCICmd.cmdID] = 1
            self.sendCmd(VNF_CONTROLLER_QUEUE,
                MSG_TYPE_VNF_CONTROLLER_CMD, addSFCICmd)

    def recvAllCmdReplys(self):
        while len(self.waitingCmdDict) > 0:
            cmdRply = self.mediatorRecvCmdRply()
            if self.waitingCmdDict.has_key(cmdRply.cmdID) \
                and cmdRply.cmdState == CMD_STATE_SUCCESSFUL:
                del self.waitingCmdDict[cmdRply.cmdID]
            else:
                assert True == False

    def delVNFI4Server(self, sfciNum=MAX_SFCI):
        logging.warning("Deleting VNFI")
        for sfciIndex in range(sfciNum):
            sfci = self.sfciList[sfciIndex]
            delSFCICmd = self.mediator.genCMDDelSFCI(self.sfc, sfci)
            self.sendCmd(VNF_CONTROLLER_QUEUE, MSG_TYPE_VNF_CONTROLLER_CMD, delSFCICmd)
            cmdRply = self.mediatorRecvCmdRply()
            assert cmdRply.cmdID == delSFCICmd.cmdID
            assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def mediatorRecvCmdRply(self):
        while True:
            msg = self.mediatorRcvAgent.getMsg(MEDIATOR_QUEUE)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            else:
                body = msg.getbody()
                if self.mediatorRcvAgent.isCommandReply(body):
                    logging.info("mediator:recvCmdRply")
                    return body
                else:
                    logging.error("Unknown massage body")

    def genSFCIList(self):
        self.sfciList = []
        for sfciIndex in range(MAX_SFCI):
            self.sfci = self.genBiDirection10BackupSFCI()
            self.sfciList.append(self.sfci)

    def genAddSFCICmdList(self):
        self.addSFCICmdList = []
        for sfciIndex in range(MAX_SFCI):
            sfci = self.sfciList[sfciIndex]
            addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, sfci)
            logging.info("sfci id: {0}".format(sfci.sfciID))
            self.addSFCICmdList.append(addSFCICmd)

    def gen10BackupVNFISequence(self, SFCLength=1):
        # hard-code function
        logging.info("use override function")
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
                vnfi = VNFI(VNF_TYPE_FW, vnfType=VNF_TYPE_FW, 
                    vnfiID=uuid.uuid1(), node=server, config={"ACL":self.genTestFWRules()})
                vnfi.maxCPUNum = 1
                vnfiSequence[index].append(vnfi)
        return vnfiSequence

    def genTestFWRules(self):
        rules = []
        for idx in range(100):
            sport1 = random.randint(100, 60000)
            sport2 = random.randint(100, 60000)
            dport1 = random.randint(100, 60000)
            dport2 = random.randint(100, 60000)
            rules.append(ACLTuple(ACL_ACTION_ALLOW, proto=ACL_PROTO_TCP, srcAddr=OUTTER_CLIENT_IP, dstAddr=WEBSITE_REAL_IP, 
                srcPort=(min(sport1,sport2), max(sport1,sport2)), dstPort=(min(dport1,dport2), max(dport1,dport2))))
        rules.append(ACLTuple(ACL_ACTION_ALLOW))
        return rules


if __name__ == "__main__":
    t = TestVNFSFCIAdderClass()
    t.measure()
