#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging

from ryu.controller import dpset

from sam.ryu.baseApp import BaseApp
from sam.ryu.topoCollector import TopoCollector


class TestBaseAppClass(object):
    @classmethod
    def setup_class(cls):
        """ setup any state specific to the execution of the given class (which
        usually contains tests).
        """
        cls.baseAppApp = BaseApp(dpset=dpset,TopoCollector=TopoCollector)

    @classmethod
    def teardown_class(cls):
        """ teardown any state that was previously setup with a call to
        setup_class.
        """

    def test_isLANIP(self):
        result = self.baseAppApp._isLANIP("2.2.1.1","2.2.1.0/24")
        assert result == True

        result = self.baseAppApp._isLANIP("10.2.3.4","11.0.0.0/8")
        assert result == False

    def test_getLANNet(self):
        result = self.baseAppApp._getLANNet(1)
        assert result == "2.2.0.32/27"

    def test_isLANIP(self):
        result = self.baseAppApp._isLANIP("10.0.0.1","10.0.0.0/8")
        assert result == True

    def test_getSwitchGatewayIP(self):
        result = self.baseAppApp._getSwitchGatewayIP(1)
        assert result == "2.2.0.33"
