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
from sam.test.FRR.testFRR import TestFRR


class TestNotViaAndReMappingClass(TestFRR):
    @pytest.fixture(scope="function")
    def setup_addUniSFCI(self):
        # setup
        self.sP = ShellProcessor()
        self.clearQueue()

        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genUniDirectionSFC(classifier)
        self.sfci = self.genUniDirection12BackupSFCI()
        self.SFCIID = self.sfci.SFCIID
        self.VNFISequence = self.sfci.VNFISequence
        self.newSfci = self.genReMappingUniDirection12BackupSFCI(self.SFCIID, self.VNFISequence)

        self.mediator = MediatorStub()
        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.sfci)
        self.delSFCICmd = self.mediator.genCMDDelSFCI(self.sfc, self.sfci)
        self.reAddSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.newSfci)

        self.runClassifierController()
        self.addSFCI2Classifier()

        self.runSFFController()
        self.addSFCI2SFF()

        self.vC = VNFControllerStub()
        self.addVNFI2Server()

        yield
        # teardown
        self.delVNFI4Server()
        self.delSFCI2SFF()
        self.delSFCI2Classifier()
        self.killClassifierController()
        self.killSFFController()

    def genUniDirection12BackupForwardingPathSet(self):
        primaryForwardingPath = {1:[[10001,1,2,10002],[10002,2,1,10001]]}
        frrType = "NotVia"
        # {(srcID,dstID,pathID):forwardingPath}
        backupForwardingPath = {
            1:{
                (1,2,2):[[1,3,2]],
                (2,1,3):[[2,3,1]]
            }
        }
        return ForwardingPathSet(primaryForwardingPath, frrType,
            backupForwardingPath)

    def genReMappingUniDirection12BackupSFCI(self, SFCIID, VNFISequence):
        return SFCI(SFCIID, VNFISequence, None,
            self.genNewUniDirection12BackupForwardingPathSet())

    def genNewUniDirection12BackupForwardingPathSet(self):
        primaryForwardingPath = {1:[[10001,1,2,10004],[10004,2,1,10001]]}
        frrType = "NotVia"
        # {(srcID,dstID,pathID):forwardingPath}
        backupForwardingPath = {
            1:{
                (1,2,2):[[1,3,2]],
                (2,1,3):[[2,3,1]]
            }
        }
        return ForwardingPathSet(primaryForwardingPath, frrType,
            backupForwardingPath)

    # @pytest.mark.skip(reason='Temporarly')
    def test_addUniSFCI(self, setup_addUniSFCI):
        print("You need start ryu-manager and mininet manually!"
            "Then press any key to continue!")
        raw_input()
        # exercise: mapping SFCI
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(NETWORK_CONTROLLER_QUEUE,
            MSG_TYPE_NETWORK_CONTROLLER_CMD,
            self.addSFCICmd)

        # verify
        print("Start listening on mediator queue")
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

        # exercise: remapping SFCI
        print("Start listening on MININET_TESTER_QUEUE"
            "Please run mode 1 in mininet test2.py")
        cmd = self.recvCmd(MININET_TESTER_QUEUE)
        if cmd.cmdType == CMD_TYPE_TESTER_REMAP_SFCI:
            # exercise
            print("Start remapping the sfci")
            self.delSFCICmd.cmdID = uuid.uuid1()
            self.sendCmd(NETWORK_CONTROLLER_QUEUE,
                MSG_TYPE_NETWORK_CONTROLLER_CMD,
                self.delSFCICmd)

            # verify
            print("Start listening on mediator queue")
            cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
            assert cmdRply.cmdID == self.delSFCICmd.cmdID
            assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

            # exercise
            self.reAddSFCICmd.cmdID = uuid.uuid1()
            self.sendCmd(NETWORK_CONTROLLER_QUEUE,
                MSG_TYPE_NETWORK_CONTROLLER_CMD,
                self.reAddSFCICmd)

            # verify
            print("Start listening on mediator queue")
            cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
            assert cmdRply.cmdID == self.reAddSFCICmd.cmdID
            assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        else:
            print("cmdType:{0}".format(cmd.cmdType))

        print("Press any key to quit!")
        raw_input()
