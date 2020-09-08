#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
import time

import pytest
from ryu.controller import dpset

from sam.ryu.topoCollector import TopoCollector
from sam.base.shellProcessor import ShellProcessor
from sam.test.testBase import *
from sam.test.fixtures.vnfControllerStub import *


class TestFRR(TestBase):
    def clearQueue(self):
        self.sP.runShellCommand("sudo rabbitmqctl purge_queue MEDIATOR_QUEUE")
        self.sP.runShellCommand(
            "sudo rabbitmqctl purge_queue NETWORK_CONTROLLER_QUEUE")
        self.sP.runShellCommand(
            "sudo rabbitmqctl purge_queue SFF_CONTROLLER_QUEUE")
        self.sP.runShellCommand(
            "sudo rabbitmqctl purge_queue SERVER_CLASSIFIER_CONTROLLER_QUEUE")
        self.sP.runShellCommand(
            "sudo rabbitmqctl purge_queue MININET_TESTER_QUEUE")

    def addSFCI2Classifier(self):
        print("setup add SFCI to classifier")
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SERVER_CLASSIFIER_CONTROLLER_QUEUE,
            MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, self.addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def addSFCI2SFF(self):
        print("setup add SFCI to sff")
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SFF_CONTROLLER_QUEUE,
            MSG_TYPE_SSF_CONTROLLER_CMD , self.addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def delSFCI2Classifier(self):
        print("teardown delete SFCI to classifier")
        self.delSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SERVER_CLASSIFIER_CONTROLLER_QUEUE,
            MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, self.delSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def delSFCI2SFF(self):
        print("teardown delete SFCI to sff")
        self.delSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SFF_CONTROLLER_QUEUE,
            MSG_TYPE_SSF_CONTROLLER_CMD , self.delSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def addVNFI2Server(self):
        print("setup add SFCI to server")
        try:
            # In normal case, there should be a timeout error!
            shellCmdRply = self.vC.installVNF("t1", "123", "192.168.122.134",
                self.sfci.VNFISequence[0][0].VNFIID)
            print("command reply:\n stdin:{0}\n stdout:{1}\n stderr:{2}".format(
                None,
                shellCmdRply['stdout'].read().decode('utf-8'),
                shellCmdRply['stderr'].read().decode('utf-8')))
        except:
            print("If raise IOError: reading from stdin while output is captured")
            print("Then pytest should use -s option!")

        try:
            # In normal case, there should be a timeout error!
            shellCmdRply = self.vC.installVNF("t1", "123", "192.168.122.208",
                self.sfci.VNFISequence[0][1].VNFIID)
            print("command reply:\n stdin:{0}\n stdout:{1}\n stderr:{2}".format(
                None,
                shellCmdRply['stdout'].read().decode('utf-8'),
                shellCmdRply['stderr'].read().decode('utf-8')))
        except:
            print("If raise IOError: reading from stdin while output is captured")
            print("Then pytest should use -s option!")

        try:
            # In normal case, there should be a timeout error!
            shellCmdRply = self.vC.installVNF("t1", "123", "192.168.122.135",
                self.sfci.VNFISequence[0][2].VNFIID)
            print("command reply:\n stdin:{0}\n stdout:{1}\n stderr:{2}".format(
                None,
                shellCmdRply['stdout'].read().decode('utf-8'),
                shellCmdRply['stderr'].read().decode('utf-8')))
        except:
            print("If raise IOError: reading from stdin while output is captured")
            print("Then pytest should use -s option!")

    def delVNFI4Server(self):
        print("teardown del SFCI from server")
        self.vC.uninstallVNF("t1", "123", "192.168.122.134",
                    self.sfci.VNFISequence[0][0].VNFIID)
        self.vC.uninstallVNF("t1", "123", "192.168.122.208",
                    self.sfci.VNFISequence[0][1].VNFIID)
        self.vC.uninstallVNF("t1", "123", "192.168.122.135",
                    self.sfci.VNFISequence[0][2].VNFIID)
        time.sleep(10)
        # Here is a bug
        print("Sometimes, we can't delete VNFI, you should delete it manually"
            "Command: sudo docker stop name1"
            )





