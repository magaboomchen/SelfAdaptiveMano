from sam.base.messageAgent import *
from sam.base.command import *
from sam.base.sfc import *
from sam.base.vnf import *

class VNFControllerStub(object):
    def __init__(self):
        self.mA = MessageAgent()
        self.mA.startRecvMsg(VNF_CONTROLLER_QUEUE)
    
    def sendCmdRply(self,cmdRply):
        msg = SAMMessage(MSG_TYPE_VNF_CONTROLLER_CMD_REPLY, cmdRply)
        self.mA.sendMsg(MEDIATOR_QUEUE,msg)