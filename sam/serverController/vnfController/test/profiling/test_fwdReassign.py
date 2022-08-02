#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
manual send traffic

eno2 1Gbps
sudo python ./sendSFCTraffic.py -i eno2 -smac 18:66:da:86:4c:16 -dmac 00:1b:21:c0:8f:98 -osip 2.2.0.36 -odip 10.16.1.1 -isip 1.1.1.1 -idip 3.3.3.3
sudo python ./sendSFCTraffic.py -i eno2 -smac 18:66:da:86:4c:16 -dmac 00:1b:21:c0:8f:98 -osip 2.2.0.36 -odip 10.16.2.1 -isip 1.1.1.1 -idip 3.3.3.3

enp4s0 10Gbps intel 82599es
sudo python ./sendSFCTraffic.py -i enp4s0 -smac 00:1b:21:c0:8f:ae -dmac 00:1b:21:c0:8f:98 -osip 2.2.0.36 -odip 10.16.1.1 -isip 1.1.1.1 -idip 3.3.3.3
'''

import uuid
import logging

import pytest

from sam.base.compatibility import screenInput
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.vnf import VNFI, VNF_TYPE_FORWARD
from sam.base.server import Server, SERVER_TYPE_NORMAL
from sam.serverController.serverManager.serverManager import SERVERID_OFFSET
from sam.base.command import CMD_STATE_SUCCESSFUL
from sam.base.messageAgent import SFF_CONTROLLER_QUEUE, VNF_CONTROLLER_QUEUE, \
    MSG_TYPE_SFF_CONTROLLER_CMD, MSG_TYPE_VNF_CONTROLLER_CMD, MEDIATOR_QUEUE
from sam.base.shellProcessor import ShellProcessor
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.test.testBase import TestBase, CLASSIFIER_DATAPATH_IP

MANUAL_TEST = True
TESTER_SERVER_DATAPATH_IP = "2.2.0.36"
TESTER_SERVER_DATAPATH_MAC = "f4:e9:d4:a3:53:a0"

SFF0_DATAPATH_IP = "2.2.0.38"
SFF0_DATAPATH_MAC = "00:1b:21:c0:8f:98"
SFF0_CONTROLNIC_IP = "192.168.0.173"
SFF0_CONTROLNIC_MAC = "18:66:da:85:1c:c3"


class TestVNFSFCIAdderClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_addSFCI(self):
        # setup
        logConfigur = LoggerConfigurator(__name__,
            './log', 'testVNFSFCIAdderClass.log', level='debug')
        self.logger = logConfigur.getLogger()

        self.sP = ShellProcessor()
        self.clearQueue()
        self.killAllModule()

        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc1 = self.genBiDirectionSFC(classifier)
        self.sfci1 = self.genBiDirection10BackupSFCI()
        self.sfc2 = self.genBiDirectionSFC(classifier)
        self.sfci2 = self.genBiDirection10BackupSFCI()
        self._reassignVNFI2SFCI()

        self.mediator = MediatorStub()
        self.server = self.genTesterServer(TESTER_SERVER_DATAPATH_IP,
            TESTER_SERVER_DATAPATH_MAC)

        self.runSFFController()
        self.runVNFController()

        yield
        # teardown
        self.delVNFI4Server()
        self.killSFFController()
        self.killVNFController()

    def _reassignVNFI2SFCI(self):
        vnfiID = self.sfci1.vnfiSequence[0][0].vnfiID
        self.sfci2.vnfiSequence[0][0].vnfiID = vnfiID

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
                vnfi = VNFI(VNF_TYPE_FORWARD, vnfType=VNF_TYPE_FORWARD, 
                    vnfiID=uuid.uuid1(), node=server)
                vnfiSequence[index].append(vnfi)
        return vnfiSequence

    def addSFCI2SFF(self):
        self.logger.info("setup add SFCI to sff")
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SFF_CONTROLLER_QUEUE,
            MSG_TYPE_SFF_CONTROLLER_CMD, self.addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def delVNFI4Server(self):
        self.logger.warning("Deleting VNFII")
        self.delSFCICmd = self.mediator.genCMDDelSFCI(self.sfc1, self.sfci1)
        self.sendCmd(VNF_CONTROLLER_QUEUE, MSG_TYPE_VNF_CONTROLLER_CMD, self.delSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def test_addSFCI(self, setup_addSFCI):
        # exercise
        self.logger.info("exercise")
        self.addSFCI1()
        self.addSFCI2()

        # verifiy
        self.logger.info("please start performance profiling" \
            "after profiling, press any key to quit.")
        screenInput()

    def addSFCI1(self):
        self.addSFCI1Cmd = self.mediator.genCMDAddSFCI(self.sfc1, self.sfci1)
        self.sendCmd(SFF_CONTROLLER_QUEUE, MSG_TYPE_SFF_CONTROLLER_CMD, self.addSFCI1Cmd)
        self.verifyCmd1Rply()

        self.addSFCI1Cmd.cmdID = uuid.uuid1()
        self.sendCmd(VNF_CONTROLLER_QUEUE, MSG_TYPE_VNF_CONTROLLER_CMD, self.addSFCI1Cmd)
        self.verifyCmd1Rply()

    def addSFCI2(self):
        self.addSFCI2Cmd = self.mediator.genCMDAddSFCI(self.sfc2, self.sfci2)
        self.sendCmd(SFF_CONTROLLER_QUEUE, MSG_TYPE_SFF_CONTROLLER_CMD, self.addSFCI2Cmd)
        self.verifyCmd2Rply()

        self.addSFCI2Cmd.cmdID = uuid.uuid1()
        self.sendCmd(VNF_CONTROLLER_QUEUE, MSG_TYPE_VNF_CONTROLLER_CMD, self.addSFCI2Cmd)
        self.verifyCmd2Rply()

    def verifyCmd1Rply(self):
        # verify cmd1
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCI1Cmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def verifyCmd2Rply(self):
        # verify cmd2
        self.logger.info("verify cmd2")
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCI2Cmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
