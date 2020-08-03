import pytest
from sam.base.socketConverter import *


MANUAL_TEST = True

class TestSocketConverterClass(object):
    def setup_method(self, method):
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """
        self.sc = SocketConverter()

    def teardown_method(self, method):
        """ teardown any state that was previously setup with a setup_method
        call.
        """
        self.sc = None
    
    def test_ipPrefix2Mask(self):
        assert self.sc.ipPrefix2Mask(32) == "255.255.255.255"
        assert self.sc.ipPrefix2Mask(31) == "255.255.255.254"
        assert self.sc.ipPrefix2Mask(24) == "255.255.255.0"
        assert self.sc.ipPrefix2Mask(16) == "255.255.0.0"
        assert self.sc.ipPrefix2Mask(8) == "255.0.0.0"