#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging

import pytest

from sam import base
from sam.base.compatibility import screenInput
from sam.base.path import ForwardingPathSet, MAPPING_TYPE_NOTVIA_PSFC
from sam.base.shellProcessor import ShellProcessor
from sam.base.messageAgent import MessageAgent
from sam.test.testBase import CLASSIFIER_DATAPATH_IP
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.test.Testbed.triangleTopo.testbedFRR import TestbedFRR

logging.basicConfig(level=logging.INFO)
logging.getLogger("pika").setLevel(logging.WARNING)


class TestPSFCClass(TestbedFRR):
    @pytest.fixture(scope="function")
    def setup_addUniSFCI(self):
        # setup
        self.resetRabbitMQConf(
            base.__file__[:base.__file__.rfind("/")] + "/rabbitMQConf.json",
            "192.168.0.194", "mq", "123456")
        self.sP = ShellProcessor()
        self.clearQueue()
        self.killAllModule()

        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genUniDirectionSFC(classifier)
        self.sfci = self.genUniDirection12BackupSFCI()

        self.mediator = MediatorStub()
        self.addSFCCmd = self.mediator.genCMDAddSFC(self.sfc)
        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.sfci)
        self.delSFCICmd = self.mediator.genCMDDelSFCI(self.sfc, self.sfci)

        self._messageAgent = MessageAgent()

        self.runClassifierController()
        self.addSFCI2Classifier()

        self.runSFFController()
        self.addSFCI2SFF()

        self.runVNFController()
        self.addVNFI2Server()

        yield
        # teardown
        self.delVNFI4Server()
        self.delSFCI2SFF()
        self.delSFCI2Classifier()
        self.killClassifierController()
        self.killSFFController()

    def genUniDirection12BackupForwardingPathSet(self):
        primaryForwardingPath = {1:[[(0,10001),(0,1),(0,2),(0,10003)],
                                    [(1,10003),(1,2),(1,1),(1,10001)]]}
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
        screenInput() 

        self.addSFC2NetworkController()
        self.addSFCI2NetworkController()

        logging.info("Please input 'ssf' to test "
            "server software failure\n"
            "After the test, "
            "Press any key to continue!")
        self.testName = screenInput() 
        if self.testName == "ssf":
            self.sendHandleServerSoftwareFailureCmd()

        logging.info("Please input 'ovs-vsctl del-br br1' to disable switch s2. "
            "After the test, Press any key to quit!")
        screenInput() 
