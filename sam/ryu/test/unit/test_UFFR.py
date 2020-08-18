import pytest
import sys
from ryu.controller import dpset
from sam.ryu.topoCollector import TopoCollector
from sam.test.testBase import *

class TestUFFRClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_addSFCI(self):
        # setup
        classifier = self.genClassifier(datapathIfIP = SFF1_DATAPATH_IP)
        self.sfc = self.genUniDirectionSFC(classifier)
        self.sfci = self.genUniDirection11BackupSFCI()
        self.mS = MediatorStub()
        self.addSFCICmd = self.mS.genCMDAddSFCI(self.sfc,self.sfci)
        yield
        # teardown

    def test_UFFRAddSFCI(self,setup_addSFCI):
        # exercise 
        self.sendCmd(NETWORK_CONTROLLER_QUEUE,
            MSG_TYPE_NETWORK_CONTROLLER_CMD,
            self.addSFCICmd)

        # verify
        print("Start listening on mediator queue")
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
    
    def printVNFISequence(self,VNFISequence):
        for vnf in VNFISequence:
            for vnfi in vnf:
                print("VNFID:{0},VNFIID:{1}".format(vnfi.VNFID,vnfi.VNFIID))