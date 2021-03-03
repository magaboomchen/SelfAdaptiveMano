#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
import time
import logging

import pytest
from ryu.controller import dpset

from sam.ryu.topoCollector import TopoCollector
from sam.base.command import *
from sam.base.shellProcessor import ShellProcessor
from sam.base.messageAgent import *
from sam.test.testBase import *
from sam.test.fixtures.vnfControllerStub import *

TESTER_SERVER_DATAPATH_MAC = "18:66:da:85:f9:ed"
OUTTER_CLIENT_IP = "1.1.1.2"
WEBSITE_REAL_IP = "3.3.3.3"

CLASSIFIER_DATAPATH_IP = "2.2.0.36"
CLASSIFIER_DATAPATH_MAC = "00:1b:21:c0:8f:ae"
CLASSIFIER_CONTROL_IP = "192.168.0.194"
CLASSIFIER_SERVERID = 10001

SFF1_DATAPATH_IP = "2.2.0.66"
SFF1_DATAPATH_MAC = "b8:ca:3a:65:f7:fa"
SFF1_CONTROLNIC_IP = "192.168.8.17"
SFF1_CONTROLNIC_MAC = "b8:ca:3a:65:f7:f8"
SFF1_SERVERID = 10002

SFF2_DATAPATH_IP = "2.2.0.68"
SFF2_DATAPATH_MAC = "ec:f4:bb:da:39:45"
SFF2_CONTROLNIC_IP = "192.168.8.18"
SFF2_CONTROLNIC_MAC = "ec:f4:bb:da:39:44"
SFF2_SERVERID = 10003

SFF3_DATAPATH_IP = "2.2.0.98"
SFF3_DATAPATH_MAC = "00:1b:21:c0:8f:98"
SFF3_CONTROLNIC_IP = "192.168.0.173"
SFF3_CONTROLNIC_MAC = "18:66:da:85:1c:c3"
SFF3_SERVERID = 10004

SFF4_DATAPATH_IP = "2.2.0.100"
SFF4_DATAPATH_MAC = "00:1b:21:c0:8f:98"
SFF4_CONTROLNIC_IP = "192.168.0.127"
SFF4_CONTROLNIC_MAC = "18:66:da:85:f9:ee"
SFF4_SERVERID = 10005


class TestbedFRR(TestBase):
    def cleanLog(self):
        self.sP.runShellCommand("rm -rf ./log")

    def addSFCI2Classifier(self):
        self.logger.info("setup add SFCI to classifier")
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SERVER_CLASSIFIER_CONTROLLER_QUEUE,
                        MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, self.addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def delSFCI2Classifier(self):
        self.logger.info("teardown delete SFCI to classifier")
        self.delSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SERVER_CLASSIFIER_CONTROLLER_QUEUE,
                        MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, self.delSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def addSFCI2SFF(self):
        self.logger.info("setup add SFCI to sff")
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SFF_CONTROLLER_QUEUE,
                        MSG_TYPE_SFF_CONTROLLER_CMD , self.addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def delSFCI2SFF(self):
        self.logger.info("teardown delete SFCI to sff")
        self.delSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SFF_CONTROLLER_QUEUE,
                        MSG_TYPE_SFF_CONTROLLER_CMD , self.delSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def addVNFI2Server(self):
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(VNF_CONTROLLER_QUEUE,
                        MSG_TYPE_VNF_CONTROLLER_CMD , self.addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def delVNFI4Server(self):
        self.logger.warning("Deleting VNFI")
        self.delSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(VNF_CONTROLLER_QUEUE,
                        MSG_TYPE_VNF_CONTROLLER_CMD , self.delSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def addSFC2NetworkController(self):
        self.addSFCCmd.cmdID = uuid.uuid1()
        queueName = self._messageAgent.genQueueName(
            NETWORK_CONTROLLER_QUEUE, self.zoneName)
        self.sendCmd(queueName,
                    MSG_TYPE_NETWORK_CONTROLLER_CMD,
                    self.addSFCCmd)
        # verify
        self.logger.info("Start listening on mediator queue")
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCCmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def addSFCI2NetworkController(self):
        self.addSFCICmd.cmdID = uuid.uuid1()
        queueName = self._messageAgent.genQueueName(
            NETWORK_CONTROLLER_QUEUE, self.zoneName)
        self.sendCmd(queueName,
                        MSG_TYPE_NETWORK_CONTROLLER_CMD,
                        self.addSFCICmd)
        # verify
        self.logger.info("Start listening on mediator queue")
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def sendHandleServerSoftwareFailureCmd(self):
        self.logger.info("sendHandleServerFailureCmd")
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

    def _updateDib(self):
        self._dib.updateServersByZone(self.topologyDict["servers"],
            PICA8_ZONE)
        self._dib.updateSwitchesByZone(self.topologyDict["switches"],
            PICA8_ZONE)
        self._dib.updateLinksByZone(self.topologyDict["links"],
            PICA8_ZONE)

        self._dib.updateSwitch2ServerLinksByZone(PICA8_ZONE)

    def runClassifierController(self):
        filePath = classifierControllerCommandAgent.__file__
        self.sP.runPythonScript(filePath)

    def runSFFController(self):
        filePath = sffControllerCommandAgent.__file__
        self.sP.runPythonScript(filePath+" "+PICA8_ZONE)
    
    def runVNFController(self):
        filePath = vnfController.__file__
        self.sP.runPythonScript(filePath+" "+PICA8_ZONE)

    def runServerManager(self):
        filePath = serverManager.__file__
        self.sP.runPythonScript(filePath+" "+PICA8_ZONE)
