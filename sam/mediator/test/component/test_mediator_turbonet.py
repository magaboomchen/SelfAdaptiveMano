#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging

import pytest

from sam.base.messageAgent import MSG_TYPE_MEDIATOR_CMD, P4CONTROLLER_QUEUE, \
    SERVER_CLASSIFIER_CONTROLLER_QUEUE, SFF_CONTROLLER_QUEUE, \
    NETWORK_CONTROLLER_QUEUE, MEDIATOR_QUEUE, \
    ORCHESTRATOR_QUEUE, TURBONET_ZONE, VNF_CONTROLLER_QUEUE, MessageAgent
from sam.base.command import CommandReply, \
    CMD_TYPE_ADD_SFCI, CMD_TYPE_GET_SERVER_SET, \
    CMD_STATE_SUCCESSFUL, CMD_STATE_FAIL
from sam.base.shellProcessor import ShellProcessor
from sam.test.fixtures.orchestrationStub import OrchestrationStub
from sam.test.fixtures.measurementStub import MeasurementStub
from sam.test.fixtures.serverManagerStub import ServerManagerStub
from sam.test.testBase import TestBase, CLASSIFIER_DATAPATH_IP

MANUAL_TEST = True

# TODO: CMD_TYPE_ADD_SFC_SUCCESSFUL, CMD_TYPE_ADD_SFC_FAIL
# need to be test

logging.basicConfig(level=logging.INFO)


class TestMediatorClass(TestBase):
    def setup_method(self, method):
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """
        self.clearQueue()
        self.killAllModule()
        self.cleanLog()

        self.oS = OrchestrationStub()
        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genBiDirectionSFC(classifier)
        self.sfci = self.genBiDirection10BackupSFCI()
        self.server = self.genTesterServer("192.168.8.17",
            "fe:54:00:05:4d:7d")
        self.mA = MessageAgent()
        self.sP = ShellProcessor()
        self.mS = MeasurementStub()
        self.sMS = ServerManagerStub()

    def teardown_method(self, method):
        """ teardown any state that was previously setup with a setup_method
        call.
        """

    @pytest.fixture(scope="function")
    def setup_startMediator(self):
        # setup
        self.runMediator()
        yield
        # teardown
        self.killMediator()

    # @pytest.mark.skip(reason='Saving time')
    def test_CMD_TYPE_ADD_SFCI_SUCCESSFUL(self, setup_startMediator):
        # orchestration send command, P4Controller
        # SFFController recv command
        addSFCICmd = self.oS.genCMDAddSFCI(self.sfc, self.sfci,
                                            source=ORCHESTRATOR_QUEUE,
                                            zone=TURBONET_ZONE)
        self.sendCmd(MEDIATOR_QUEUE, MSG_TYPE_MEDIATOR_CMD, addSFCICmd)

        p4ControllerQueueName = self.mA.genQueueName(P4CONTROLLER_QUEUE,
                                                            TURBONET_ZONE)
        logging.info("listen on {0}".format(p4ControllerQueueName))
        recvCmdP4Ctl = self.recvCmd(p4ControllerQueueName)
        assert recvCmdP4Ctl.cmdType == CMD_TYPE_ADD_SFCI
        sffControllerQueueName = self.mA.genQueueName(SFF_CONTROLLER_QUEUE,
                                                            TURBONET_ZONE)

        logging.info("listen on {0}".format(sffControllerQueueName))
        recvCmdSFFCtl = self.recvCmd(sffControllerQueueName)
        assert recvCmdSFFCtl.cmdType == CMD_TYPE_ADD_SFCI

        # p4Controller,SFFController
        # send command reply
        recvCmdP4CtlRply =  CommandReply(recvCmdP4Ctl.cmdID,
            CMD_STATE_SUCCESSFUL)
        self.sMS.sendCmdRply(recvCmdP4CtlRply)

        recvCmdSFFCtlRply =  CommandReply(recvCmdSFFCtl.cmdID,
            CMD_STATE_SUCCESSFUL)
        self.sMS.sendCmdRply(recvCmdSFFCtlRply)

        # mediator recv command reply from SFFController, 
        # VNFController recv command
        vnfControllerQueueName = self.mA.genQueueName(VNF_CONTROLLER_QUEUE,
                                                            TURBONET_ZONE)
        logging.info("listen on {0}".format(vnfControllerQueueName))
        recvCmdVNFCtl = self.recvCmd(vnfControllerQueueName)
        assert recvCmdVNFCtl.cmdType == CMD_TYPE_ADD_SFCI

        # vnfController send command reply
        recvCmdVNFCtlRply =  CommandReply(recvCmdVNFCtl.cmdID,
                                            CMD_STATE_SUCCESSFUL)
        self.sMS.sendCmdRply(recvCmdVNFCtlRply)

        # orchestration recv command reply
        logging.info("listen on {0}".format(ORCHESTRATOR_QUEUE))
        recvCmdRply = self.recvCmdRply(ORCHESTRATOR_QUEUE)
        assert recvCmdRply.cmdID == addSFCICmd.cmdID
        assert recvCmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def test_CMD_TYPE_ADD_SFCI_FAIL(self,setup_startMediator):
        # orchestration send command, P4Controller
        # SFFController recv command
        addSFCICmd = self.oS.genCMDAddSFCI(self.sfc, self.sfci,
                                            source=ORCHESTRATOR_QUEUE,
                                            zone=TURBONET_ZONE)
        self.sendCmd(MEDIATOR_QUEUE, MSG_TYPE_MEDIATOR_CMD, addSFCICmd)

        p4ControllerQueueName = self.mA.genQueueName(P4CONTROLLER_QUEUE,
                                                            TURBONET_ZONE)
        logging.info("listen on {0}".format(p4ControllerQueueName))
        recvCmdP4Ctl = self.recvCmd(p4ControllerQueueName)
        assert recvCmdP4Ctl.cmdType == CMD_TYPE_ADD_SFCI
        sffControllerQueueName = self.mA.genQueueName(SFF_CONTROLLER_QUEUE,
                                                            TURBONET_ZONE)

        logging.info("listen on {0}".format(sffControllerQueueName))
        recvCmdSFFCtl = self.recvCmd(sffControllerQueueName)
        assert recvCmdSFFCtl.cmdType == CMD_TYPE_ADD_SFCI

        # p4Controller,SFFController
        # send command reply
        recvCmdP4CtlRply =  CommandReply(recvCmdP4Ctl.cmdID,
            CMD_STATE_SUCCESSFUL)
        self.sMS.sendCmdRply(recvCmdP4CtlRply)

        recvCmdSFFCtlRply =  CommandReply(recvCmdSFFCtl.cmdID,
            CMD_STATE_SUCCESSFUL)
        self.sMS.sendCmdRply(recvCmdSFFCtlRply)

        # mediator recv command reply from SFFController, 
        # VNFController recv command
        vnfControllerQueueName = self.mA.genQueueName(VNF_CONTROLLER_QUEUE,
                                                            TURBONET_ZONE)
        logging.info("listen on {0}".format(vnfControllerQueueName))
        recvCmdVNFCtl = self.recvCmd(vnfControllerQueueName)
        assert recvCmdVNFCtl.cmdType == CMD_TYPE_ADD_SFCI

        # vnfController send command reply
        recvCmdVNFCtlRply =  CommandReply(recvCmdVNFCtl.cmdID,
                                            CMD_STATE_FAIL)
        self.sMS.sendCmdRply(recvCmdVNFCtlRply)

        # orchestration recv command reply
        logging.info("listen on {0}".format(ORCHESTRATOR_QUEUE))
        recvCmdRply = self.recvCmdRply(ORCHESTRATOR_QUEUE)
        assert recvCmdRply.cmdID == addSFCICmd.cmdID
        assert recvCmdRply.cmdState == CMD_STATE_FAIL
