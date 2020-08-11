import pytest
import uuid
from sam.base.server import *
from sam.base.command import *
from sam.test.fixtures.orchestrationStub import *
from sam.base.messageAgent import *
from sam.test.testBase import *
from sam.mediator.mediator import *
from sam.base.command import *

MANUAL_TEST = True

class TestMediatorClass(TestBase):
    def setup_method(self, method):
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """
        self.mA = MessageAgent()

    def teardown_method(self, method):
        """ teardown any state that was previously setup with a setup_method
        call.
        """

    def test_isCommand(self):
        body = Command(1,2)
        assert self.mA.isCommand(body) == True
        body = 1
        assert self.mA.isCommand(body) == False

    def test_isCommandReply(self):
        body = CommandReply(1,2)
        assert self.mA.isCommandReply(body) == True
        body = 1
        assert self.mA.isCommandReply(body) == False