#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging

from sam.base.topoGen.base.dhcpServer import DHCPServer

MANUAL_TEST = True

logging.basicConfig(level=logging.INFO)


class TestDHCPServerClass(object):
    def setup_method(self, method):
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """
        self.ds = DHCPServer()

    def teardown_method(self, method):
        """ teardown any state that was previously setup with a setup_method
        call.
        """
        pass

    def test_assignIP(self):
        ip = self.ds.assignIP(0)
        assert ip == "2.2.0.2"
