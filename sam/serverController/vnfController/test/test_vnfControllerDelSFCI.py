#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging
from scapy.all import *
import time

import pytest

from sam.base.sfc import *
from sam.base.vnf import *
from sam.base.server import *
from sam.base.command import *
from sam.base.socketConverter import *
from sam.base.shellProcessor import ShellProcessor
from sam.test.fixtures.mediatorStub import *
from sam.test.fixtures.vnfControllerStub import *
from sam.test.testBase import *
from sam.serverController.classifierController import *

MANUAL_TEST = True
TESTER_SERVER_DATAPATH_IP = "2.2.0.199"
TESTER_SERVER_DATAPATH_MAC = "52:54:00:a8:b0:a1"

SFF0_DATAPATH_IP = "2.2.0.200"
SFF0_DATAPATH_MAC = "52:54:00:5a:14:f0"
SFF0_CONTROLNIC_IP = "192.168.0.201"
SFF0_CONTROLNIC_MAC = "52:54:00:1f:51:12"
logging.basicConfig(level=logging.INFO)

class TestVNFSFCIDeleterClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_delSFCI(self):
        # setup
        self.resetRabbitMQConf(
            "/home/t1/Projects/SelfAdaptiveMano/sam/base/rabbitMQConf.conf",
            "192.168.0.158", "mq", "123456")
        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genBiDirectionSFC(classifier)
        self.sfci = self.genBiDirection10BackupSFCI()
        self.mediator = MediatorStub()
        self.sP = ShellProcessor()
        self.sP.runShellCommand("sudo rabbitmqctl purge_queue MEDIATOR_QUEUE")
        self.sP.runShellCommand(
            "sudo rabbitmqctl purge_queue VNF_CONTROLLER_QUEUE")
        #self.server = self.genTesterServer(TESTER_SERVER_DATAPATH_IP,
        #    TESTER_SERVER_DATAPATH_MAC)
        self.runSFFController()
        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.sfci)
        self.addSFCI2SFF()
        self.runVNFController()

        yield

        self.killSFFController()
        self.killVNFController()
    
    # def resetRabbitMQConf(self, filePath, serverIP,
    #         serverUser, serverPasswd):
    #     with open(filePath, 'w') as f:
    #         f.write("RABBITMQSERVERIP = '{0}'\n".format(serverIP))
    #         f.write("RABBITMQSERVERUSER = '{0}'\n".format(serverUser))
    #         f.write("RABBITMQSERVERPASSWD = '{0}'\n".format(serverPasswd))
    
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
                vnfi = VNFI(VNF_TYPE_FORWARD, VNFType=VNF_TYPE_FORWARD, 
                    VNFIID=uuid.uuid1(), node=server)
                vnfi.maxCPUNum = 1
                VNFISequence[index].append(vnfi)
        return VNFISequence

    # def runSFFController(self):
    #     filePath = "~/Projects/SelfAdaptiveMano/sam/serverController/sffController/sffControllerCommandAgent.py"
    #     self.sP.runPythonScript(filePath)

    # def killSFFController(self):
    #     self.sP.killPythonScript("sffControllerCommandAgent.py")

    def addSFCI2SFF(self):
        logging.info("setup add SFCI to sff")
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SFF_CONTROLLER_QUEUE,
            MSG_TYPE_SSF_CONTROLLER_CMD , self.addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    # def runVNFController(self):
    #     filePath = "~/Projects/SelfAdaptiveMano/sam/serverController/vnfController/vnfController.py"
    #     self.sP.runPythonScript(filePath)

    # def killVNFController(self):
    #     self.sP.killPythonScript("vnfController.py")

    def test_delSFCI(self, setup_delSFCI):
        # exercise
        logging.info("exercise")
        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.sfci)
        self.sendCmd(VNF_CONTROLLER_QUEUE,
            MSG_TYPE_VNF_CONTROLLER_CMD , self.addSFCICmd)
        addCmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert addCmdRply.cmdID == self.addSFCICmd.cmdID
        assert addCmdRply.cmdState == CMD_STATE_SUCCESSFUL

        logging.info("Finish adding sfci.")
        logging.info("Wait for deleting sfci.")

        time.sleep(10)
        logging.info("Deleting sfci.")
        self.delSFCICmd = self.mediator.genCMDDelSFCI(self.sfc, self.sfci)
        self.sendCmd(VNF_CONTROLLER_QUEUE,
            MSG_TYPE_VNF_CONTROLLER_CMD, self.delSFCICmd)
        delCmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert delCmdRply.cmdID == self.delSFCICmd.cmdID
        assert delCmdRply.cmdState == CMD_STATE_SUCCESSFUL