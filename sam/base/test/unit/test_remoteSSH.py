import pytest
from sam.base.sshProcessor import *

MANUAL_TEST = True

class TestRemoteSSHClass(object):
    def setup_method(self, method):
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """
        self.rS = SSHProcessor()
        self.rS.connectSSH("t1", "123", "192.168.122.134", remoteSSHPort=22)

    def teardown_method(self, method):
        """ teardown any state that was previously setup with a setup_method
        call.
        """

    def test_runShellCommand(self):
        self.rS.runShellCommand("ls")