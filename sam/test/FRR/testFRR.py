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
from sam.test.testBase import *
from sam.test.fixtures.vnfControllerStub import *

logging.basicConfig(level=logging.INFO)


class TestFRR(TestBase):
    def addSFCI2Classifier(self):
        logging.info("setup add SFCI to classifier")
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SERVER_CLASSIFIER_CONTROLLER_QUEUE,
            MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, self.addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def addSFCI2SFF(self):
        logging.info("setup add SFCI to sff")
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SFF_CONTROLLER_QUEUE,
            MSG_TYPE_SFF_CONTROLLER_CMD , self.addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def delSFCI2Classifier(self):
        logging.info("teardown delete SFCI to classifier")
        self.delSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SERVER_CLASSIFIER_CONTROLLER_QUEUE,
            MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, self.delSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def delSFCI2SFF(self):
        logging.info("teardown delete SFCI to sff")
        self.delSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SFF_CONTROLLER_QUEUE,
            MSG_TYPE_SFF_CONTROLLER_CMD , self.delSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def addVNFI2Server(self):
        logging.info("setup add SFCI to server")
        try:
            # In normal case, there should be a timeout error!
            shellCmdRply = self.vC.installVNF("t1", "123", "192.168.122.134",
                self.sfci.vnfiSequence[0][0].vnfiID)
            logging.info("command reply:\n stdin:{0}\n stdout:{1}\n stderr:{2}".format(
                None,
                shellCmdRply['stdout'].read().decode('utf-8'),
                shellCmdRply['stderr'].read().decode('utf-8')))
        except:
            logging.info("If raise IOError: reading from stdin while output is captured")
            logging.info("Then pytest should use -s option!")

        try:
            # In normal case, there should be a timeout error!
            shellCmdRply = self.vC.installVNF("t1", "123", "192.168.122.135",
                self.sfci.vnfiSequence[0][1].vnfiID)
            logging.info("command reply:\n stdin:{0}\n stdout:{1}\n stderr:{2}".format(
                None,
                shellCmdRply['stdout'].read().decode('utf-8'),
                shellCmdRply['stderr'].read().decode('utf-8')))
        except:
            logging.info("If raise IOError: reading from stdin while output is captured")
            logging.info("Then pytest should use -s option!")

        try:
            # In normal case, there should be a timeout error!
            shellCmdRply = self.vC.installVNF("t1", "123", "192.168.122.208",
                self.sfci.vnfiSequence[0][2].vnfiID)
            logging.info("command reply:\n stdin:{0}\n stdout:{1}\n stderr:{2}".format(
                None,
                shellCmdRply['stdout'].read().decode('utf-8'),
                shellCmdRply['stderr'].read().decode('utf-8')))
        except:
            logging.info("If raise IOError: reading from stdin while output is captured")
            logging.info("Then pytest should use -s option!")

    def delVNFI4Server(self):
        logging.info("teardown del SFCI from server")
        self.vC.uninstallVNF("t1", "123", "192.168.122.134",
                    self.sfci.vnfiSequence[0][0].vnfiID)
        self.vC.uninstallVNF("t1", "123", "192.168.122.135",
                    self.sfci.vnfiSequence[0][1].vnfiID)
        self.vC.uninstallVNF("t1", "123", "192.168.122.208",
                    self.sfci.vnfiSequence[0][2].vnfiID)
        time.sleep(10)
        # Here is a bug
        logging.info("Sometimes, we can't delete VNFI, you should delete it manually"
            "Command: sudo docker stop name1"
            )

    def sendHandleServerFailureCmd(self):
        logging.info("sendHandleServerFailureCmd")
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
