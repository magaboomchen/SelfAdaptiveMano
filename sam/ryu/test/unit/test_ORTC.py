#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
import logging

from sam.base.loggerConfigurator import LoggerConfigurator
try:
    set
except NameError:
    from sets import Set as set

import pytest

from sam.ryu.ufrrIBMaintainer import UFRRIBMaintainer


class TestORTCClass(object):
    @pytest.fixture(scope="function")
    def setup_addRuleSet1(self):
        logConfigur = LoggerConfigurator(__name__,
            './log', 'testORTCClass.log', level='debug')
        self.logger = logConfigur.getLogger()

        self.urm = UFRRIBMaintainer()
        self.urm.addSFCIUFRRFlowTableEntry(dpid=1, sfciID=1, vnfID=1, pathID=1,
                                            actions={"output nodeID": 1})
        self.urm.addSFCIUFRRFlowTableEntry(dpid=1, sfciID=2, vnfID=1, pathID=1,
                                            actions={"output nodeID": 2})
        self.urm.addSFCIUFRRFlowTableEntry(dpid=1, sfciID=3, vnfID=1, pathID=1,
                                            actions={"output nodeID": 2})

    # @pytest.mark.skip(reason='Temporarly')
    def test_v4Compression(self, setup_addRuleSet1):
        self.urm.initialBinaryTrieForAllSwitches(v6=False)
        self.urm.countSwitchCompressedFlowTableOfORTC(dpid=1)
        self.urm.compressAllSwitchesUFRRTableByORTC()
        self.urm.countSwitchCompressedFlowTableOfORTC(dpid=1)

    @pytest.mark.skip(reason='Temporarly')
    def test_v6Compression(self, setup_addRuleSet1):
        self.logger.info(self.urm.switchesUFRRTable.keys())
        self.urm.initialBinaryTrieForAllSwitches(v6=True)
        self.urm.countSwitchCompressedFlowTableOfORTC(dpid=1, v6=True)
        self.urm.compressAllSwitchesUFRRTableByORTC(v6=True)
        self.urm.countSwitchCompressedFlowTableOfORTC(dpid=1, v6=True)
