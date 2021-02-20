#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
import time
import logging

import pytest
from ryu.controller import dpset

from sam.ryu.topoCollector import TopoCollector
from sam.base.path import *
from sam.base.shellProcessor import ShellProcessor
from sam.test.testBase import *
from sam.test.fixtures.vnfControllerStub import *
from sam.test.FRR.testFRR import TestFRR

logging.basicConfig(level=logging.INFO)


class TestPSFCClass(TestFRR):
    @pytest.fixture(scope="function")
    def setup_addUniSFCI(self):
        # setup
        self.sP = ShellProcessor()
        self.clearQueue()
        self.killAllModule()

        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genUniDirectionSFC(classifier)
        self.sfci = self.genUniDirection12BackupSFCI()
        # self.sfciID = self.sfci.sfciID
        # self.vnfiSequence = self.sfci.vnfiSequence

        self.mediator = MediatorStub()
        self.addSFCCmd = self.mediator.genCMDAddSFC(self.sfc)
        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.sfci)
        self.delSFCICmd = self.mediator.genCMDDelSFCI(self.sfc, self.sfci)

        self._messageAgent = MessageAgent()

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
        primaryForwardingPath = {1:[[(0,10001),(0,1),(0,2),(0,10003)],[(1,10003),(1,2),(1,1),(1,10001)]]}
        mappingType = MAPPING_TYPE_NOTVIA_PSFC
        # To test notVia ryu app simplily, we set merge switch as the failure node
        backupForwardingPath = {
            1:{
                (("failureNPoPID", (0, 2, (1,))),
                ("repairMethod", "increaseBackupPathPrioriy")):
                    [[(0, 1), (0, 3), (0, 10005)], [(1, 10005), (1, 3), (1, 1)]]
            }
        }
        return ForwardingPathSet(primaryForwardingPath, mappingType,
            backupForwardingPath)

    # @pytest.mark.skip(reason='Temporarly')
    def test_addUniSFCI(self, setup_addUniSFCI):
        logging.info("You need start ryu-manager and mininet manually!"
            "Then press any key to continue!")
        raw_input()

        # exercise: mapping SFC
        self.addSFCCmd.cmdID = uuid.uuid1()
        self.sendCmd(NETWORK_CONTROLLER_QUEUE,
            MSG_TYPE_NETWORK_CONTROLLER_CMD,
            self.addSFCCmd)

        # verify
        logging.info("Start listening on mediator queue")
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCCmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

        # exercise: mapping SFCI
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(NETWORK_CONTROLLER_QUEUE,
            MSG_TYPE_NETWORK_CONTROLLER_CMD,
            self.addSFCICmd)

        # verify
        logging.info("Start listening on mediator queue")
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

        logging.info("Please input any key to test "
            "server software failure\n"
            "After the test, "
            "Press any key to quit!")
        raw_input()
        self.sendHandleServerFailureCmd()

        logging.info("Please break down sff 1\n"
            "After the test, "
            "Press any key to quit!")
        raw_input()

        logging.info("Press any key to quit!")
        raw_input()
