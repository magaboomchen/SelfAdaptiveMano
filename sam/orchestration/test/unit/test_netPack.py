#!/usr/bin/python
# -*- coding: UTF-8 -*-

import pytest

from sam.orchestration.algorithms.netPack.netPack import NetPack
from sam.measurement.dcnInfoBaseMaintainer import *
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer


class TestNetPackClass(object):
    @classmethod
    def setup_class(cls):
        cls.tc = TestNetPackClass()

        # setup
        logConfigur = LoggerConfigurator(__name__, level='info')
        cls.logger = logConfigur.getLogger()

    @classmethod
    def teardown_class(cls):
        pass

    @pytest.mark.skip(reason='Temporarly')
    def test_isSwitchInSubTopologyZone(self):
        # exercise
        dib = None
        requestList = None
        podNum = 4
        minPodIdx = 0
        maxPodIdx = 1
        self.nP = NetPack(dib, requestList, podNum, minPodIdx, maxPodIdx)
        self.nP.isSwitchInSubTopologyZone(1)

        # verify
        assert 1 == 1

    # @pytest.mark.skip(reason='Temporarly')
    def test_getAllServerSets(self):
        # exercise
        dib = None
        requestList = None
        podNum = 4
        minPodIdx = 0
        maxPodIdx = 1
        self.nP = NetPack(dib, requestList, podNum, minPodIdx, maxPodIdx)
        res = self.nP.getAllServerSets()
        for _ in res:
            self.logger.info(_)

        # verify
        assert 1 == 1
