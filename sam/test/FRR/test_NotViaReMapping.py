#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
deprecated test
needs modify forwarding path set format
'''

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

class TestNotViaAndReMappingClass(TestFRR):
    @pytest.fixture(scope="function")
    def setup_addUniSFCI(self):
        # setup
        self.sP = ShellProcessor()
        self.clearQueue()

        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genUniDirectionSFC(classifier)
        self.sfci = self.genUniDirection12BackupSFCI()
        self.sfciID = self.sfci.sfciID
        self.vnfiSequence = self.sfci.vnfiSequence
        self.newSfci = self.genReMappingUniDirection12BackupSFCI(self.sfciID, self.vnfiSequence)

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
        # primaryForwardingPath = {1:[[10001,1,2,10002],[10002,2,1,10001]]}
        primaryForwardingPath = {1:[[(0,10001),(0,1),(0,2),(0,10002)],[(1,10002),(1,2),(1,1),(1,10001)]]}
        mappingType = MAPPING_TYPE_NOTVIA
        # {(srcID,dstID,pathID):forwardingPath}
        # backupForwardingPath = {
        #     1:{
        #         (1,2,2):[[1,3,2]],
        #         (2,1,3):[[2,3,1]]
        #     }
        # }
        # To test notVia ryu app simplily, we set merge switch as the failure node
        backupForwardingPath = {
            1:{
                (("failureLayerNodeID", (0,2)), ("repairMethod", "fast-reroute"),
                    ("repairLayerSwitchID", (0, 1)),
                    ("mergeLayerSwitchID", (0, 2)), ("newPathID", 2)):
                        [[(0,1),(0,3),(0,10003)],[(1,10003),(1,3),(1,1),(1,10001)]],
                (("failureLayerNodeID", (1,1)), ("repairMethod", "fast-reroute"),
                    ("repairLayerSwitchID", (1, 2)),
                    ("mergeLayerSwitchID", (1, 1)), ("newPathID", 3)):
                        [[(1,2),(1,3),(1,1)]]
            }
        }
        return ForwardingPathSet(primaryForwardingPath, mappingType,
            backupForwardingPath)

    def genReMappingUniDirection12BackupSFCI(self, sfciID, vnfiSequence):
        return SFCI(sfciID, vnfiSequence, None,
            self.genNewUniDirection12BackupForwardingPathSet())

    def genNewUniDirection12BackupForwardingPathSet(self):
        primaryForwardingPath = {1:[[10001,1,2,10004],[10004,2,1,10001]]}
        mappingType = "NotVia"
        # {(srcID,dstID,pathID):forwardingPath}
        backupForwardingPath = {
            1:{
                (1,2,2):[[1,3,2]],
                (2,1,3):[[2,3,1]]
            }
        }
        return ForwardingPathSet(primaryForwardingPath, mappingType,
            backupForwardingPath)

    # @pytest.mark.skip(reason='Temporarly')
    def test_addUniSFCI(self, setup_addUniSFCI):
        logging.info("You need start ryu-manager and mininet manually!"
            "Then press any key to continue!")
        raw_input()
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

        # exercise: remapping SFCI
        logging.info("Start listening on MININET_TESTER_QUEUE"
            "Please run mode 1 in mininet test2.py")
        cmd = self.recvCmd(MININET_TESTER_QUEUE)
        if cmd.cmdType == CMD_TYPE_TESTER_REMAP_SFCI:
            # exercise
            logging.info("Start remapping the sfci")
            self.delSFCICmd.cmdID = uuid.uuid1()
            self.sendCmd(NETWORK_CONTROLLER_QUEUE,
                MSG_TYPE_NETWORK_CONTROLLER_CMD,
                self.delSFCICmd)

            # verify
            logging.info("Start listening on mediator queue")
            cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
            assert cmdRply.cmdID == self.delSFCICmd.cmdID
            assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

            # exercise
            self.reAddSFCICmd.cmdID = uuid.uuid1()
            self.sendCmd(NETWORK_CONTROLLER_QUEUE,
                MSG_TYPE_NETWORK_CONTROLLER_CMD,
                self.reAddSFCICmd)

            # verify
            logging.info("Start listening on mediator queue")
            cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
            assert cmdRply.cmdID == self.reAddSFCICmd.cmdID
            assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        else:
            logging.info("cmdType:{0}".format(cmd.cmdType))

        logging.info("Press any key to quit!")
        raw_input()
