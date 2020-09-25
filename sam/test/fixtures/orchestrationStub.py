from sam.base.messageAgent import *
from sam.base.command import *
from sam.base.sfc import *
from sam.base.vnf import *

class OrchestrationStub(object):
    def __init__(self):
        self.mA = MessageAgent()
        # self.mA.startRecvMsg(ORCHESTRATOR_QUEUE)

    def genCMDAddSFCI(self,sfc,sfci):
        cmdID = uuid.uuid1()
        attr = {'sfc':sfc,'sfci':sfci,'sfcUUID':sfc.sfcUUID}
        cmd = Command(CMD_TYPE_ADD_SFCI,cmdID,attr)
        return cmd

    def genCMDDelSFCI(self,sfc,sfci):
        cmdID = uuid.uuid1()
        attr = {'sfc':sfc,'sfci':sfci,'sfcUUID':sfc.sfcUUID}
        cmd = Command(CMD_TYPE_DEL_SFCI,cmdID,attr)
        return cmd
    
    def genCMDGetServer(self):
        cmdID = uuid.uuid1()
        cmd = Command(CMD_TYPE_GET_SERVER_SET,cmdID)
        return cmd
    
    def genCMDGetTopo(self):
        cmdID = uuid.uuid1()
        cmd = Command(CMD_TYPE_GET_TOPOLOGY,cmdID)
        return cmd
    
    def genCMDGetSFCI(self,sfc,sfci):
        cmdID = uuid.uuid1()
        attr = {'sfci':sfci,'sfcUUID':sfc.sfcUUID}
        cmd = Command(CMD_TYPE_GET_SFCI_STATE,cmdID,attr)
        return cmd