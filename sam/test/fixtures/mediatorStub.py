from sam.base.messageAgent import *
from sam.base.command import *
from sam.test.fixtures.orchestrationStub import *


class MediatorStub(OrchestrationStub):
    def __init__(self):
        self.mA = MessageAgent()

    def genCMDAddSFCI(self,sfc,sfci):
        cmdID = uuid.uuid1()
        attr = {'sfc':sfc,'sfci':sfci}
        cmd = Command(CMD_TYPE_ADD_SFCI,cmdID,attr)
        return cmd

    def genCMDDelSFCI(self,sfc,sfci):
        cmdID = uuid.uuid1()
        attr = {'sfc':sfc,'sfci':sfci}
        cmd = Command(CMD_TYPE_DEL_SFCI,cmdID,attr)
        return cmd

    def genCMDDelSFC(self,sfc):
        cmdID = uuid.uuid1()
        attr = {'sfc':sfc}
        cmd = Command(CMD_TYPE_DEL_SFC,cmdID,attr)
        return cmd
