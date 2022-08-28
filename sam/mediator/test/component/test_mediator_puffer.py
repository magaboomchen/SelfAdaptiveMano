#!/usr/bin/python
# -*- coding: UTF-8 -*-

import pytest

from sam.mediator import mediator
from sam.base.messageAgent import MSG_TYPE_MEDIATOR_CMD, \
    SERVER_CLASSIFIER_CONTROLLER_QUEUE, SFF_CONTROLLER_QUEUE, \
    NETWORK_CONTROLLER_QUEUE, MEDIATOR_QUEUE, \
    ORCHESTRATOR_QUEUE, VNF_CONTROLLER_QUEUE
from sam.base.command import CommandReply, \
    CMD_TYPE_ADD_SFCI, CMD_TYPE_GET_SERVER_SET, \
    CMD_STATE_SUCCESSFUL, CMD_STATE_FAIL
from sam.base.shellProcessor import ShellProcessor
from sam.test.fixtures.orchestrationStub import OrchestrationStub
from sam.test.fixtures.measurementStub import MeasurementStub
from sam.test.fixtures.serverManagerStub import ServerManagerStub
from sam.test.testBase import TestBase, CLASSIFIER_DATAPATH_IP

# TODO: CMD_TYPE_GET_SFCI_STATE, CMD_TYPE_GET_TOPOLOGY, CMD_TYPE_DEL_SFCI
# need to be test


class TestMediatorClass(TestBase):
    def setup_method(self, method):
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """
        self.oS = OrchestrationStub()
        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genBiDirectionSFC(classifier)
        self.sfci = self.genBiDirection10BackupSFCI()
        self.server = self.genTesterServer("192.168.123.1",
            "fe:54:00:05:4d:7d")
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
        scriptsPath = mediator.__file__
        self.sP.runPythonScript(scriptsPath)
        yield
        # teardown
        self.sP.killPythonScript("mediator/mediator.py")

    # @pytest.mark.skip(reason='Saving time')
    def test_CMD_TYPE_ADD_SFCI_SUCCESSFUL(self,setup_startMediator):
        # orchestration send command, networkController,classifierController
        # SFFController recv command
        addSFCICmd = self.oS.genCMDAddSFCI(self.sfc,self.sfci)
        self.sendCmd(MEDIATOR_QUEUE, MSG_TYPE_MEDIATOR_CMD, addSFCICmd)
        recvCmdNetworkCtl = self.recvCmd(NETWORK_CONTROLLER_QUEUE)
        assert recvCmdNetworkCtl.cmdType == CMD_TYPE_ADD_SFCI
        recvCmdClassifierCtl = self.recvCmd(SERVER_CLASSIFIER_CONTROLLER_QUEUE)
        assert recvCmdClassifierCtl.cmdType == CMD_TYPE_ADD_SFCI
        recvCmdSFFCtl = self.recvCmd(SFF_CONTROLLER_QUEUE)
        assert recvCmdSFFCtl.cmdType == CMD_TYPE_ADD_SFCI

        # networkController,classifierController,SFFController
        # send command reply
        recvCmdNetworkCtlRply =  CommandReply(recvCmdNetworkCtl.cmdID,
            CMD_STATE_SUCCESSFUL)
        self.sMS.sendCmdRply(recvCmdNetworkCtlRply)

        recvCmdClassifierCtlRply =  CommandReply(recvCmdClassifierCtl.cmdID,
            CMD_STATE_SUCCESSFUL)
        self.sMS.sendCmdRply(recvCmdClassifierCtlRply)

        recvCmdSFFCtlRply =  CommandReply(recvCmdSFFCtl.cmdID,
            CMD_STATE_SUCCESSFUL)
        self.sMS.sendCmdRply(recvCmdSFFCtlRply)

        # mediator recv command reply from SFFController, 
        # VNFController recv command
        recvCmdVNFCtl = self.recvCmd(VNF_CONTROLLER_QUEUE)
        assert recvCmdVNFCtl.cmdType == CMD_TYPE_ADD_SFCI

        # vnfController send command reply
        recvCmdVNFCtlRply =  CommandReply(recvCmdVNFCtl.cmdID,
            CMD_STATE_SUCCESSFUL)
        self.sMS.sendCmdRply(recvCmdVNFCtlRply)

        # orchestration recv command reply
        recvCmdRply = self.recvCmdRply(ORCHESTRATOR_QUEUE)
        assert recvCmdRply.cmdID == addSFCICmd.cmdID
        assert recvCmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def test_CMD_TYPE_ADD_SFCI_FAIL(self,setup_startMediator):
        # orchestration send command, networkController,classifierController
        # SFFController recv command
        addSFCICmd = self.oS.genCMDAddSFCI(self.sfc,self.sfci)
        self.sendCmd(MEDIATOR_QUEUE,MSG_TYPE_MEDIATOR_CMD,addSFCICmd)
        recvCmdNetworkCtl = self.recvCmd(NETWORK_CONTROLLER_QUEUE)
        assert recvCmdNetworkCtl.cmdType == CMD_TYPE_ADD_SFCI
        recvCmdClassifierCtl = self.recvCmd(SERVER_CLASSIFIER_CONTROLLER_QUEUE)
        assert recvCmdClassifierCtl.cmdType == CMD_TYPE_ADD_SFCI
        recvCmdSFFCtl = self.recvCmd(SFF_CONTROLLER_QUEUE)
        assert recvCmdSFFCtl.cmdType == CMD_TYPE_ADD_SFCI

        # networkController,classifierController,SFFController
        # send command reply
        recvCmdNetworkCtlRply =  CommandReply(recvCmdNetworkCtl.cmdID,
            CMD_STATE_SUCCESSFUL)
        self.sMS.sendCmdRply(recvCmdNetworkCtlRply)

        recvCmdClassifierCtlRply =  CommandReply(recvCmdClassifierCtl.cmdID,
            CMD_STATE_SUCCESSFUL)
        self.sMS.sendCmdRply(recvCmdClassifierCtlRply)

        recvCmdSFFCtlRply =  CommandReply(recvCmdSFFCtl.cmdID,
            CMD_STATE_FAIL)
        self.sMS.sendCmdRply(recvCmdSFFCtlRply)

        # mediator recv command reply from SFFController, 
        # orchestration recv command reply
        recvCmdRply = self.recvCmdRply(ORCHESTRATOR_QUEUE)
        assert recvCmdRply.cmdID == addSFCICmd.cmdID
        assert recvCmdRply.cmdState == CMD_STATE_FAIL