#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid
import logging

import pytest

from sam.base.switch import SWITCH_TYPE_NPOP
from sam.base.messageAgent import MSG_TYPE_CLASSIFIER_CONTROLLER_CMD
from sam.base.command import CommandReply, CMD_STATE_SUCCESSFUL
from sam.test.fixtures.orchestrationStub import OrchestrationStub
from sam.mediator.mediator import Mediator
from sam.test.testBase import TestBase, CLASSIFIER_DATAPATH_IP

MANUAL_TEST = True

logging.basicConfig(level=logging.INFO)


class TestMediatorClass(TestBase):
    def setup_method(self, method):
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """
        self.oS = OrchestrationStub()
        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genBiDirectionSFC(classifier)
        self.sfci = self.genBiDirection10BackupSFCI()
        self.genTesterServer("192.168.123.1","fe:54:00:05:4d:7d")
        mode = {
            'switchType': SWITCH_TYPE_NPOP,
            'classifierType': 'Server'  # 'Switch'/'Server'
        }
        self.mediator = Mediator(mode)

    def teardown_method(self, method):
        """ teardown any state that was previously setup with a setup_method
        call.
        """

    def test_commandHandler_CMD_TYPE_ADD_SFCI(self, mocker):
        # setup-cont
        mocker.patch.object(self.mediator, '_addSFCI2ClassifierController')
        mocker.patch.object(self.mediator, '_addSFCI2NetworkController')
        mocker.patch.object(self.mediator, '_addSFCI2SFFController')
        mocker.patch.object(self.mediator, '_prepareChildCmd')
        # exercise
        addSFCICmd = self.oS.genCMDAddSFCI(self.sfc, self.sfci)
        # verify
        self.mediator._commandHandler(addSFCICmd)
        self.mediator._addSFCI2ClassifierController.assert_called_once()
        self.mediator._addSFCI2NetworkController.assert_called_once()
        self.mediator._addSFCI2SFFController.assert_called_once()
        self.mediator._prepareChildCmd.assert_called_once()

    def test_commandHandler_CMD_TYPE_DEL_SFCI(self, mocker):
        # setup-cont
        mocker.patch.object(self.mediator, '_delSFCI4ClassifierController')
        mocker.patch.object(self.mediator, '_delSFCI4SFFController')
        mocker.patch.object(self.mediator, '_delSFCI4NetworkController')
        mocker.patch.object(self.mediator, '_delSFCIs4Server')
        # exercise
        delSFCICmd = self.oS.genCMDDelSFCI(self.sfc, self.sfci)
        # verify
        self.mediator._commandHandler(delSFCICmd)
        self.mediator._delSFCI4ClassifierController.assert_called_once()
        self.mediator._delSFCI4NetworkController.assert_called_once()
        self.mediator._delSFCI4SFFController.assert_called_once()
        self.mediator._delSFCIs4Server.assert_called_once()

    def test_commandHandler_CMD_TYPE_GET_SERVER_SET(self, mocker):
        # setup-cont
        mocker.patch.object(self.mediator, '_getServerSet4ServerManager')
        # exercise
        getServerCmd = self.oS.genCMDGetServer()
        # verify
        self.mediator._commandHandler(getServerCmd)
        self.mediator._getServerSet4ServerManager.assert_called_once()

    def test_commandHandler_CMD_TYPE_GET_TOPOLOGY(self,mocker):
        # setup-cont
        mocker.patch.object(self.mediator, '_getTopo4NetworkController')
        # exercise
        getTopoCmd = self.oS.genCMDGetTopo()
        # verify
        self.mediator._commandHandler(getTopoCmd)
        self.mediator._getTopo4NetworkController.assert_called_once()

    def test_commandHandler_CMD_TYPE_GET_SFCI_STATE(self, mocker):
        # setup-cont
        mocker.patch.object(self.mediator, '_getSFCIStatus4SFFP4')
        # exercise
        getSFCICmd = self.oS.genCMDGetSFCI(self.sfc, self.sfci)
        # verify
        self.mediator._commandHandler(getSFCICmd)
        self.mediator._getSFCIStatus4SFFP4.assert_called_once()

    def test_prepareChildCmd(self):
        # setup
        addSFCICmd = self.oS.genCMDAddSFCI(self.sfc, self.sfci)
        self.mediator._cm.addCmd(addSFCICmd)
        # exercise
        cCmd = self.mediator._prepareChildCmd(addSFCICmd,
            MSG_TYPE_CLASSIFIER_CONTROLLER_CMD)
        # verify
        cCmdinCM = self.mediator._cm.getCmd(cCmd.cmdID)
        assert cCmd == cCmdinCM
    
    def test_MergeDict(self):
        dict1 = {'vnfi':{'vnfid1':1,'vnfid2':2}}
        dict2 = {'sfci':self.sfci}
        self.mediator._MergeDict(dict1,dict2)
        assert dict2 == {'vnfi':{'vnfid1':1,'vnfid2':2},'sfci':self.sfci}

    @pytest.fixture(scope="function")
    def setup_genCmdRplys(self):
        self.cmdRply1 = CommandReply(uuid.uuid1(), CMD_STATE_SUCCESSFUL,
            attributes = {'vnfi':{'vnfid1':1}})
        self.cmdRply2 = CommandReply(uuid.uuid1(), CMD_STATE_SUCCESSFUL,
            attributes = {'vnfi':{'vnfid2':2}})

    def test_getMixedAttributes(self, setup_genCmdRplys):
        cCmdRplyList = [self.cmdRply1,self.cmdRply2]
        attributes = self.mediator._getMixedAttributes(cCmdRplyList)
        assert attributes == {'vnfi':{'vnfid1':1,'vnfid2':2}}