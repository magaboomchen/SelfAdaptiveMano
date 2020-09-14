from sam.base.messageAgent import *
from sam.base.command import *
from sam.base.sfc import *
from sam.base.vnf import *

class MeasurementStub(object):
    def __init__(self):
        self.mA = MessageAgent()
        # self.mA.startRecvMsg(ORCHESTRATOR_QUEUE)

    def genCMDGetServerSet(self):
        cmdID = uuid.uuid1()
        attr = {}
        cmd = Command(CMD_TYPE_GET_SERVER_SET,cmdID,attr)
        return cmd

    def genCMDGetTopo(self):
        cmdID = uuid.uuid1()
        attr = {}
        cmd = Command(CMD_TYPE_GET_TOPOLOGY,cmdID,attr)
        return cmd

    def genCMDGetSFCIState(self):
        cmdID = uuid.uuid1()
        attr = {}
        cmd = Command(CMD_TYPE_GET_SFCI_STATE,cmdID,attr)
        return cmd