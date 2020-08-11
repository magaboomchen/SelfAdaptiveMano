from sam.base.messageAgent import *
from sam.base.command import *
from sam.base.sfc import *
from sam.base.vnf import *

class ServerManagerStub(object):
    def __init__(self):
        self.mA = MessageAgent()
        # self.mA.startRecvMsg(SERVER_MANAGER_QUEUE)
    
    def sendCmdRply(self,cmdRply):
        msg = SAMMessage(MSG_TYPE_SERVER_MANAGER_CMD_REPLY, cmdRply)
        self.mA.sendMsg(MEDIATOR_QUEUE,msg)