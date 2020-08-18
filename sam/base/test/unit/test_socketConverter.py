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

    def test_int2Bytes(self):
        assert self.sc.int2Bytes(15,1) == b'\x0f'
        assert self.sc.int2Bytes(15,2) == b'\x00\x0f'
        assert self.sc.int2Bytes(61440,2) == b'\xf0\x00'
        assert self.sc.int2Bytes(61440,3) == b'\x00\xf0\x00'
        assert self.sc.int2Bytes(167776512,4) == b'\x0A\x00\x11\x00'

    def test_bytes2Int(self):
        assert self.sc.bytes2Int(b'\x00\x0F') == 15
        assert self.sc.bytes2Int(b'\x00\x00') == 0
        assert self.sc.bytes2Int(b'\xf0\x00') == 61440