#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid
import logging
from datetime import datetime

import pytest
import pickle
import base64

from sam.base.request import *
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.serverController.serverManager.serverManager import SeverManager, SERVERID_OFFSET
from sam.orchestration.algorithms.performanceModel import *
from sam.orchestration.algorithms.base.mappingAlgorithmBase import *
from sam.test.testBase import *

MANUAL_TEST = True
logging.basicConfig(level=logging.INFO)


class TestMappingAlgorithmBaseClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_mab(self):
        # setup
        self.mab = MappingAlgorithmBase()

    # @pytest.mark.skip(reason='Temporarly')
    def test_findForwardPath(self, setup_mab):
        # exercise
        path = [(7, 3), (9, 16), (3, 9), (14, 7)]
        forwardPath = self.mab._findForwardPath(path)

        # verify
        assert forwardPath == [7, 3, 9, 16]

    # @pytest.mark.skip(reason='Temporarly')
    def test_findPrevForwardPath(self, setup_mab):
        # exercise
        path = [(7, 3), (9, 16), (3, 9), (14, 7)]
        backwardPath = self.mab._findPrevForwardPath(path)

        # verify
        assert backwardPath == [14, 7]

    def test_findPrevForwardPath2(self, setup_mab):
        # exercise
        path = [(13, 4), (0, 10), (4, 0), (10, 19)]
        backwardPath = self.mab._findPrevForwardPath(path)

        # verify
        assert backwardPath == [13]

    def test_findPrevForwardPath3(self, setup_mab):
        # exercise
        path = [(2, 5), (14, 7), (7, 2), (5, 12)]
        backwardPath = self.mab._findPrevForwardPath(path)

        # verify
        assert backwardPath == [14, 7, 2]

    def test_transPath2ForwardingPath(self, setup_mab):
        # exercise
        path = [14, 7, 3, 9, 16]
        forwardingPath = self.mab._transPath2ForwardingPath(0, path)

        # verify
        # input [14, 7, 3, 9, 16]
        # return [(0, 14), (0, 7), (0, 3), (0, 9), (0, 16)]
        assert forwardingPath == [(0, 14), (0, 7), (0, 3), (0, 9), (0, 16)]

    def test_listFunction(self, setup_mab):
        tmpList = [13]
        assert tmpList[:-2] == []
