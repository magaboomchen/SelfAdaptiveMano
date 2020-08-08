import pytest
import uuid
from sam.base.server import *
from sam.base.command import *
from sam.test.fixtures.orchestrationStub import *
from sam.test.testBase import *
from sam.mediator.mediator import *

MANUAL_TEST = True

class TestMediatorClass(TestBase):
    def setup_method(self, method):
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """
        self.oS = OrchestrationStub()
        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genSFC(classifier)
        self.sfci = self.genSFCI()
        self.genTesterServer()
        mode = {
            'switchType': SWITCH_TYPE_OPENFLOW,    # SWITCH_TYPE_P4/SWITCH_TYPE_OPENFLOW
            'classifierType': 'Server'  # 'Switch'/'Server'
        }
        self.mediator = Mediator(mode)

    def teardown_method(self, method):
        """ teardown any state that was previously setup with a setup_method
        call.
        """

    def test_isCommand(self):
        body = Command(1,2)
        assert self.mediator._isCommand(body) == True
        body = 1
        assert self.mediator._isCommand(body) == False
    
    def test_isCommandReply(self):
        body = CommandReply(1,2)
        assert self.mediator._isCommandReply(body) == True
        body = 1
        assert self.mediator._isCommandReply(body) == False
    
    def test_commandHandler_CMD_TYPE_ADD_SFCI(self,mocker):
        # setup-cont
        mocker.patch.object(self.mediator,'_addSFCI2ClassifierController')
        mocker.patch.object(self.mediator,'_addSFCI2NetworkController')
        mocker.patch.object(self.mediator,'_addSFCI2BessController')
        mocker.patch.object(self.mediator,'_prepareChildCmd')
        # exercise
        addSFCICmd = self.oS.genCMDAddSFCI(self.sfc,self.sfci)
        # verify
        self.mediator._commandHandler(addSFCICmd)
        self.mediator._addSFCI2ClassifierController.assert_called_once()
        self.mediator._addSFCI2NetworkController.assert_called_once()
        self.mediator._addSFCI2BessController.assert_called_once()
        self.mediator._prepareChildCmd.assert_called_once()
    
    def test_commandHandler_CMD_TYPE_DEL_SFCI(self,mocker):
        # setup-cont
        mocker.patch.object(self.mediator,'_delSFCI4ClassifierController')
        mocker.patch.object(self.mediator,'_delSFCI4BessController')
        mocker.patch.object(self.mediator,'_delSFCI4NetworkController')
        mocker.patch.object(self.mediator,'_delSFCIs4Server')
        # exercise
        delSFCICmd = self.oS.genCMDDelSFCI(self.sfc,self.sfci)
        # verify
        self.mediator._commandHandler(delSFCICmd)
        self.mediator._delSFCI4ClassifierController.assert_called_once()
        self.mediator._delSFCI4NetworkController.assert_called_once()
        self.mediator._delSFCI4BessController.assert_called_once()
        self.mediator._delSFCIs4Server.assert_called_once()
    
    def test_commandHandler_CMD_TYPE_GET_SERVER_SET(self,mocker):
        # setup-cont
        mocker.patch.object(self.mediator,'_getServerSet4ServerManager')
        # exercise
        getServerCmd = self.oS.genCMDGetServer()
        # verify
        self.mediator._commandHandler(getServerCmd)
        self.mediator._getServerSet4ServerManager.assert_called_once()
    
    def test_commandHandler_CMD_TYPE_GET_TOPOLOGY(self,mocker):
        # setup-cont
        mocker.patch.object(self.mediator,'_getTopo4NetworkController')
        # exercise
        getTopoCmd = self.oS.genCMDGetTopo()
        # verify
        self.mediator._commandHandler(getTopoCmd)
        self.mediator._getTopo4NetworkController.assert_called_once()
    
    def test_commandHandler_CMD_TYPE_GET_SFCI_STATUE(self,mocker):
        # setup-cont
        mocker.patch.object(self.mediator,'_getSFCIStatus4ServerP4')
        # exercise
        getSFCICmd = self.oS.genCMDGetSFCI(self.sfc,self.sfci)
        # verify
        self.mediator._commandHandler(getSFCICmd)
        self.mediator._getSFCIStatus4ServerP4.assert_called_once()
    
    def test_prepareChildCmd(self):
        pass