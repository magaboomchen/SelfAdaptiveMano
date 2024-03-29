#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.command import CMD_STATE_FAIL, CMD_STATE_PROCESSING, CMD_STATE_SUCCESSFUL, CMD_STATE_WAITING
from sam.base.xibMaintainer import XInfoBaseMaintainer


class CommandMaintainer(XInfoBaseMaintainer):
    def __init__(self):
        super(CommandMaintainer, self).__init__()
        self._commandsInfo = {}

    def addCmd(self, cmd):
        self._commandsInfo[cmd.cmdID] = {
            'cmd': cmd,
            'state': CMD_STATE_WAITING,
            'cmdReply': None,
            'parentCmdID': None,
            'childCmdID': {}   # {CmdName1:cmdID,CmdName1:cmdID}
        }

    def getCmd(self, cmdID):
        if cmdID in self._commandsInfo:
            return self._commandsInfo[cmdID]['cmd']
        else:
            return None

    def hasCmd(self, cmdID):
        if cmdID in self._commandsInfo:
            return True
        else:
            return False

    def delCmdwithChildCmd(self, cmdID):
        for key, childCmdID in self._commandsInfo[cmdID]['childCmdID'].items():
            del self._commandsInfo[childCmdID]
        del self._commandsInfo[cmdID]

    def addChildCmd2Cmd(self, currentCmdID, childCmdName, childCmdID):
        self._commandsInfo[currentCmdID]['childCmdID'][childCmdName] = childCmdID

    def delChildCmd4Cmd(self, currentCmdID, childCmdName):
        del self._commandsInfo[currentCmdID]['childCmdID'][childCmdName]

    def addParentCmd2Cmd(self,currentCmdID, parentCmdID):
        self._commandsInfo[currentCmdID]['parentCmdID'] = parentCmdID

    def getCmdState(self, cmdID):
        return self._commandsInfo[cmdID]['state']

    def changeCmdState(self, cmdID, state):
        self._commandsInfo[cmdID]['state'] = state

    def transitCmdState(self, cmdID, statePrev, stateNext):
        if self.hasCmd(cmdID):
            state = self._commandsInfo[cmdID]['state']
            if state == statePrev:
                self._commandsInfo[cmdID]['state'] = stateNext

    def getChildCmdState(self, cmdID, childCmdName):
        cCmdID = self._commandsInfo[cmdID]['childCmdID'][childCmdName]
        return self._commandsInfo[cCmdID]['state']

    def getChildCmd(self, cmdID, childCmdName):
        cCmdID = self._commandsInfo[cmdID]['childCmdID'][childCmdName]
        return self._commandsInfo[cCmdID]['cmd']

    def getCmdType(self, cmdID):
        return self._commandsInfo[cmdID]['cmd'].cmdType
    
    def getParentCmdID(self,cmdID):
        return self._commandsInfo[cmdID]['parentCmdID']

    def addCmdRply(self,cmdID,cmdRply):
        self._commandsInfo[cmdID]['cmdReply'] = cmdRply

    def isChildCmdHasCmdRply(self,cmdID):
        if self._commandsInfo[cmdID]['cmdReply'] != None:
            return True
        else:
            return False

    def getChildCMdRplyList(self,parentCmdID):
        childCmdRplyList = []
        cmdInfo = self._commandsInfo[parentCmdID]
        for key, childCmdID in cmdInfo['childCmdID'].items():
            childCmdRply = self._commandsInfo[childCmdID]['cmdReply']
            childCmdRplyList.append(childCmdRply)
        return childCmdRplyList

    def isParentCmdSuccessful(self,cmdID):
        # if all child cmd is successful, then send cmdRply
        cmdInfo = self._commandsInfo[cmdID]
        for key, childCmdID in cmdInfo['childCmdID'].items():
            if self.getCmdState(childCmdID) != CMD_STATE_SUCCESSFUL:
                return False
        return True

    def isParentCmdFailed(self,cmdID):
        # if at least one child cmd is failed, then parent cmd failed
        cmdInfo = self._commandsInfo[cmdID]
        for key, childCmdID in cmdInfo['childCmdID'].items():
            if self.getCmdState(childCmdID) == CMD_STATE_FAIL:
                return True
        return False

    def isOnlyOneChildCmdFailed(self,cmdID):
        cmdInfo = self._commandsInfo[cmdID]
        count = 0
        for key, childCmdID in cmdInfo['childCmdID'].items():
            if self.getCmdState(childCmdID) == CMD_STATE_FAIL:
                count = count + 1
        if count == 1:
            return True
        else:
            return False

    def isAllChildCmdDetermined(self,cmdID):
        cmdInfo = self._commandsInfo[cmdID]
        for key, childCmdID in cmdInfo['childCmdID'].items():
            if self.getCmdState(childCmdID) == CMD_STATE_WAITING or \
                self.getCmdState(childCmdID) == CMD_STATE_PROCESSING:
                return False
        return True

    def isParentCmdWaiting(self,cmdID):
        cmdInfo = self._commandsInfo[cmdID]
        for key, childCmdID in cmdInfo['childCmdID'].items():
            if self.getCmdState(childCmdID) == CMD_STATE_WAITING:
                return True
        return False

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)
