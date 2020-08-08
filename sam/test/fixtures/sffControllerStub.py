from sam.base.messageAgent import *
from sam.base.command import *
from sam.base.sfc import *
from sam.base.vnf import *

class SFFControllerStub(object):
    def __init__(self):
        self.mA = MessageAgent()
        self.mA.startRecvMsg(SFF_CONTROLLER_QUEUE)
    
    def sendCmdRply(self,cmdRply):
        msg = SAMMessage(MSG_TYPE_SSF_CONTROLLER_CMD_REPLY, cmdRply)
        self.mA.sendMsg(MEDIATOR_QUEUE,msg)