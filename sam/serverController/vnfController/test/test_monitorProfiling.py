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
from sam.base.lb import *
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

class TestVNFAddMON(TestBase):
    @pytest.fixture(scope="function")
    def setup_addMON(self):
        # setup
        self.sP = ShellProcessor()
        self.clearQueue()

        rabbitMQFilePath = server.__file__.split("server.py")[0] \
            + "rabbitMQConf.conf"
        logging.info(rabbitMQFilePath)
        self.resetRabbitMQConf(rabbitMQFilePath, "192.168.0.194",
            "mq", "123456")

        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genBiDirectionSFC(classifier, vnfTypeSeq=[VNF_TYPE_MONITOR])
        self.sfci = self.genBiDirection10BackupSFCI()
        self.mediator = MediatorStub()

        self.server = self.genTesterServer(TESTER_SERVER_DATAPATH_IP,
            TESTER_SERVER_DATAPATH_MAC)

        self.runSFFController()
        self.runVNFController()

        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.sfci)
        self.addSFCI2SFF()

        yield
        # teardown
        # here we can't remove kill the container because we should test its tcp server in the server node (TODO)
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
                vnfi = VNFI(VNF_TYPE_MONITOR, vnfType=VNF_TYPE_MONITOR, 
                    vnfiID=uuid.uuid1(), node=server)
                vnfiSequence[index].append(vnfi)
        return vnfiSequence

    def addSFCI2SFF(self):
        logging.info("setup add SFCI to sff")
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SFF_CONTROLLER_QUEUE,
            MSG_TYPE_SFF_CONTROLLER_CMD , self.addSFCICmd)
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


    def test_addMON(self, setup_addMON):
        # exercise
        logging.info("exercise")
        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.sfci)
        self.sendCmd(VNF_CONTROLLER_QUEUE,
            MSG_TYPE_VNF_CONTROLLER_CMD , self.addSFCICmd)

        # verifiy
        self.verifyCmdRply()
        logging.info("please start performance profiling" \
            "after profiling, press any key to quit.")
        raw_input()

    def verifyCmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

