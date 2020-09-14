from sam.base.messageAgent import *
from sam.base.command import *
from sam.base.sfc import *
from sam.base.vnf import *

class ClassifierControllerStub(object):
    def __init__(self):
        self.queue = SERVER_CLASSIFIER_CONTROLLER_QUEUE
        self.mA = MessageAgent()
        # self.mA.startRecvMsg(self.queue)

    def sendCmdRply(self, cmdRply):
        msg = SAMMessage(MSG_TYPE_CLASSIFIER_CONTROLLER_CMD_REPLY, cmdRply)
        self.mA.sendMsg(MEDIATOR_QUEUE,msg)