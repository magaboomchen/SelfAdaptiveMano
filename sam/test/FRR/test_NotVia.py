#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid
import logging

import pytest

from sam.base.compatibility import screenInput
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.path import ForwardingPathSet, MAPPING_TYPE_NOTVIA_PSFC
from sam.base.shellProcessor import ShellProcessor
from sam.base.command import CMD_STATE_SUCCESSFUL
from sam.base.messageAgent import NETWORK_CONTROLLER_QUEUE, \
    MSG_TYPE_NETWORK_CONTROLLER_CMD, MEDIATOR_QUEUE
from sam.test.testBase import CLASSIFIER_DATAPATH_IP
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.test.fixtures.vnfControllerStub import VNFControllerStub
from sam.test.FRR.testFRR import TestFRR


class TestNotViaClass(TestFRR):
    @pytest.fixture(scope="function")
    def setup_addUniSFCI(self):
        # setup
        logConfigur = LoggerConfigurator(__name__, './log',
                                            'testNotViaClass.log',
                                            level='debug')
        self.logger = logConfigur.getLogger()

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
                (("failureLayerNodeID", (0,2)), ("repairMethod", "fast-reroute"),
                    ("repairLayerSwitchID", (0, 1)),
                    ("mergeLayerSwitchID", (0, 2)), ("newPathID", 2)):
                        [[(0,1),(0,3),(0,2)]],
                (("failureLayerNodeID", (1,1)), ("repairMethod", "fast-reroute"),
                    ("repairLayerSwitchID", (1, 2)),
                    ("mergeLayerSwitchID", (1, 1)), ("newPathID", 3)):
                        [[(1,2),(1,3),(1,1)]]
            }
        }
        return ForwardingPathSet(primaryForwardingPath, mappingType,
            backupForwardingPath)

    # @pytest.mark.skip(reason='Temporarly')
    def test_addUniSFCI(self, setup_addUniSFCI):
        self.logger.info("You need start ryu-manager and mininet manually!"
            "Then press any key to continue!")
        screenInput()

        self._deploySFC()
        self._deploySFCI()

        self.logger.info("Press any key to quit!")
        screenInput()

    def _deploySFC(self):
        # exercise: mapping SFC
        self.addSFCCmd.cmdID = uuid.uuid1()
        self.sendCmd(NETWORK_CONTROLLER_QUEUE,
            MSG_TYPE_NETWORK_CONTROLLER_CMD,
            self.addSFCCmd)

        # verify
        self.logger.info("Start listening on mediator queue")
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCCmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def _deploySFCI(self):
        # exercise: mapping SFCI
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(NETWORK_CONTROLLER_QUEUE,
            MSG_TYPE_NETWORK_CONTROLLER_CMD,
            self.addSFCICmd)

        # verify
        self.logger.info("Start listening on mediator queue")
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

        self.logger.info("Press any key to quit!")
        screenInput()
