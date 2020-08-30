CMD_STATE_WAITING = "CMD_STATE_WAITING"
CMD_STATE_PROCESSING = "CMD_STATE_PROCESSING"
CMD_STATE_SUCCESSFUL = "CMD_STATE_SUCCESSFUL"
CMD_STATE_FAIL = "CMD_STATE_FAIL"

CMD_TYPE_ADD_SFCI = "CMD_TYPE_ADD_SFCI"
CMD_TYPE_DEL_SFCI = "CMD_TYPE_DEL_SFCI"
CMD_TYPE_GET_SERVER_SET = "CMD_TYPE_GET_SERVER_SET"
CMD_TYPE_GET_TOPOLOGY = "CMD_TYPE_GET_TOPOLOGY"
CMD_TYPE_GET_SFCI_STATE = "CMD_TYPE_GET_SFCI_STATE"
CMD_TYPE_TESTER_REMAP_SFCI = "CMD_TYPE_TESTER_REMAP_SFCI"

class Command(object):
    def __init__(self, cmdType, cmdID, attributes={}):
        self.cmdType = cmdType
        self.cmdID = cmdID
        self.attributes = attributes    # {'sfcUUID':sfcUUID,'sfci':sfci, 'sfc':sfc, 'classifier':classifier}

class CommandReply(object):
    def __init__(self, cmdID, cmdState, attributes={}):
        self.cmdID = cmdID
        self.cmdState = cmdState
        self.attributes = attributes    # {'switches':{},'links':{},'server':{},'vnfi':{}}

class CommandMaintainer(object):
    def __init__(self):
        self._commandsInfo = {}

    def addCmd(self, cmd):
        self._commandsInfo[cmd.cmdID] = {
            'cmd': cmd,
            'state': CMD_STATE_WAITING,
            'cmdReply': None,
            'parentCmdID': None,
            'childCmdID': {}   # {CmdName1:cmdID,CmdName1:cmdID}
        }

    def delCmdwithChildCmd(self, cmdID):
        for childCmdID in self._commandsInfo[cmdID]['childCmdID'].itervalues():
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

    def getChildCmdState(self, cmdID, childCmdName):
        cCmdID = self._commandsInfo[cmdID]['childCmdID'][childCmdName]
        return self._commandsInfo[cCmdID]['state']

    def getCmdType(self, cmdID):
        return self._commandsInfo[cmdID]['cmd'].cmdType
    
    def getParentCmdID(self,cmdID):
        return self._commandsInfo[cmdID]['parentCmdID']
    
    def getCmd(self, cmdID):
        return self._commandsInfo[cmdID]['cmd']

    def addCmdRply(self,cmdID,cmdRply):
        self._commandsInfo[cmdID]['cmdReply'] = cmdRply

    def getChildCMdRplyList(self,parentCmdID):
        childCmdRplyList = []
        cmdInfo = self._commandsInfo[parentCmdID]
        for childCmdID in cmdInfo['childCmdID'].itervalues():
            childCmdRply = self._commandsInfo[childCmdID]['cmdReply']
            childCmdRplyList.append(childCmdRply)
        return childCmdRplyList

    def isParentCmdSuccessful(self,cmdID):
        cmdInfo = self._commandsInfo[cmdID]
        for childCmdID in cmdInfo['childCmdID'].itervalues():
            if self.getCmdState(childCmdID) != CMD_STATE_SUCCESSFUL:
                return False
        return True

    def isParentCmdFailed(self,cmdID):
        cmdInfo = self._commandsInfo[cmdID]
        for childCmdID in cmdInfo['childCmdID'].itervalues():
            if self.getCmdState(childCmdID) == CMD_STATE_FAIL:
                return True
        return False

    def isParentCmdWaiting(self,cmdID):
        cmdInfo = self._commandsInfo[cmdID]
        for childCmdID in cmdInfo['childCmdID'].itervalues():
            if self.getCmdState(childCmdID) == CMD_STATE_WAITING:
                return True
        return False