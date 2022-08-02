#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid
import logging

import pytest

from sam.base.command import Command, CommandReply, CMD_TYPE_ADD_SFCI, \
    CMD_TYPE_DEL_SFCI, CMD_STATE_SUCCESSFUL, CMD_STATE_WAITING, CMD_STATE_FAIL
from sam.base.commandMaintainer import CommandMaintainer
from sam.base.messageAgent import MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, MSG_TYPE_SERVER_MANAGER_CMD

MANUAL_TEST = True


class TestCommandMaintainerClass(object):
    def setup_method(self, method):
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """
        self.cm = CommandMaintainer()

        self.cmdID = uuid.uuid1()
        self.sfcUUID = uuid.uuid1()
        self.cmd = Command(CMD_TYPE_ADD_SFCI,self.cmdID,attributes={'sfcUUID':self.sfcUUID})

        self.cCmdID = uuid.uuid1()
        self.cCmd = Command(CMD_TYPE_DEL_SFCI,self.cCmdID,attributes={'sfcUUID':self.sfcUUID})

        self.cCmdID2 = uuid.uuid1()
        self.cCmd2 = Command(CMD_TYPE_DEL_SFCI,self.cCmdID2,attributes={'sfcUUID':self.sfcUUID})

        self.cmdRply = CommandReply(self.cCmdID, CMD_STATE_SUCCESSFUL)

    def teardown_method(self, method):
        """ teardown any state that was previously setup with a setup_method
        call.
        """
        self.cm = None
        self.cmd = None

    @pytest.fixture(scope="function")
    def setup_addCmdandcCmd(self):
        # setup
        # add a parent command
        self.cm._commandsInfo[self.cmdID] = {}
        self.cm._commandsInfo[self.cmdID]['cmd'] = self.cmd
        self.cm._commandsInfo[self.cmdID]['state'] = CMD_STATE_WAITING
        # add a child command
        self.cm._commandsInfo[self.cCmdID] = {}
        self.cm._commandsInfo[self.cCmdID]['cmd'] = self.cCmdID
        self.cm._commandsInfo[self.cCmdID]['state'] = CMD_STATE_WAITING
        self.cm._commandsInfo[self.cCmdID]['parentCmdID'] = self.cmdID
        # add another child command
        self.cm._commandsInfo[self.cCmdID2] = {}
        self.cm._commandsInfo[self.cCmdID2]['cmd'] = self.cCmdID2
        self.cm._commandsInfo[self.cCmdID2]['state'] = CMD_STATE_WAITING
        self.cm._commandsInfo[self.cCmdID2]['parentCmdID'] = self.cmdID
        # add child commands to parent command
        self.cm._commandsInfo[self.cmdID]['childCmdID'] = {
            MSG_TYPE_CLASSIFIER_CONTROLLER_CMD:self.cCmdID,
            MSG_TYPE_SERVER_MANAGER_CMD:self.cCmdID2
            }
        yield
        # teardown

    @pytest.fixture(scope="function")
    def setup_addCmdRply(self):
        # setup
        self.cm._commandsInfo[self.cCmdID]['cmdReply'] = self.cmdRply
        self.cm._commandsInfo[self.cCmdID2]['cmdReply'] = self.cmdRply
        yield
        # teardown

    @pytest.fixture(scope="function")
    def setup_successfulcCmd(self):
        # setup
        self.cm._commandsInfo[self.cCmdID]['state'] = CMD_STATE_SUCCESSFUL
        self.cm._commandsInfo[self.cCmdID2]['state'] = CMD_STATE_SUCCESSFUL
        yield
        # teardown

    @pytest.fixture(scope="function")
    def setup_failedcCmd(self):
        # setup
        self.cm._commandsInfo[self.cCmdID]['state'] = CMD_STATE_FAIL
        yield
        # teardown

    def test_addCmd(self):
        self.cm.addCmd(self.cmd)
        assert self.cm._commandsInfo[self.cmdID]['cmd'] == self.cmd

    def test_delCmdwithChildCmd(self, setup_addCmdandcCmd):
        self.cm.delCmdwithChildCmd(self.cmdID)
        assert self.cm._commandsInfo == {}

    def test_addChildCmd2Cmd(self, setup_addCmdandcCmd):
        self.cm.addChildCmd2Cmd(self.cmdID,MSG_TYPE_CLASSIFIER_CONTROLLER_CMD,self.cCmdID)
        assert self.cm._commandsInfo[self.cmdID]['childCmdID']\
            [MSG_TYPE_CLASSIFIER_CONTROLLER_CMD] == self.cCmdID

    def test_delChildCmd4Cmd(self,setup_addCmdandcCmd):
        self.cm.delChildCmd4Cmd(self.cmdID,MSG_TYPE_CLASSIFIER_CONTROLLER_CMD)
        childCmdKey = self.cm._commandsInfo[self.cmdID]['childCmdID'].keys()
        assert not MSG_TYPE_CLASSIFIER_CONTROLLER_CMD in childCmdKey

    def test_getCmdState(self,setup_addCmdandcCmd):
        state = self.cm.getCmdState(self.cmdID)
        assert state == CMD_STATE_WAITING

    def test_changeCmdState(self,setup_addCmdandcCmd):
        self.cm.changeCmdState(self.cmdID,CMD_STATE_SUCCESSFUL)
        state = self.cm._commandsInfo[self.cmdID]['state']
        assert  state == CMD_STATE_SUCCESSFUL
    
    def test_addParentCmd2Cmd(self,setup_addCmdandcCmd):
        self.cm.addParentCmd2Cmd(self.cCmdID,self.cmdID)
        assert self.cm._commandsInfo[self.cCmdID]['parentCmdID'] == self.cmdID
    
    def test_getChildCmdState(self,setup_addCmdandcCmd):
        state = self.cm.getChildCmdState(self.cmdID,MSG_TYPE_CLASSIFIER_CONTROLLER_CMD)
        assert state == CMD_STATE_WAITING
    
    def test_getCmdType(self,setup_addCmdandcCmd):
        assert self.cm.getCmdType(self.cmdID) == CMD_TYPE_ADD_SFCI
    
    def test_getParentCmdID(self,setup_addCmdandcCmd):
        assert self.cm.getParentCmdID(self.cCmdID) == self.cmdID
    
    def test_getCmd(self,setup_addCmdandcCmd):
        assert self.cm.getCmd(self.cmdID) == self.cmd
    
    def test_addCmdRply(self,setup_addCmdandcCmd):
        self.cm.addCmdRply(self.cCmdID,self.cmdRply)
        assert self.cm._commandsInfo[self.cCmdID]['cmdReply'] == self.cmdRply
    
    def test_getChildCMdRplyList(self,setup_addCmdandcCmd,setup_addCmdRply):
        ccrl = self.cm.getChildCMdRplyList(self.cmdID)
        assert ccrl == [self.cmdRply,self.cmdRply]
    
    def test_isParentCmdSuccessful_Case1(self,setup_addCmdandcCmd):
        assert self.cm.isParentCmdSuccessful(self.cmdID) == False
    
    def test_isParentCmdSuccessful_Case2(self,setup_addCmdandcCmd,
        setup_successfulcCmd):
        assert self.cm.isParentCmdSuccessful(self.cmdID) == True
    
    def test_isParentCmdFailed_Case1(self,setup_addCmdandcCmd):
        assert self.cm.isParentCmdFailed(self.cmdID) == False
    
    def test_isParentCmdFailed_Case2(self,setup_addCmdandcCmd,
        setup_failedcCmd):
        assert self.cm.isParentCmdFailed(self.cmdID) == True
    
    def test_isParentCmdWaiting(self,setup_addCmdandcCmd):
        assert self.cm.isParentCmdWaiting(self.cmdID) == True
    
    def test_isParentCmdWaiting(self,setup_addCmdandcCmd,
        setup_successfulcCmd):
        assert self.cm.isParentCmdWaiting(self.cmdID) == False