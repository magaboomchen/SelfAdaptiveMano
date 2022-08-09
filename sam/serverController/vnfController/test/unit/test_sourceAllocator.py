#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
Usage:
    (1) sudo env "PATH=$PATH" python -m pytest ./test_vnfControllerAddFW.py -s --disable-warnings
    (2) Please run 'python  ./serverAgent.py  0000:06:00.0  enp1s0  nfvi  2.2.0.98'
        on the NFVI running bess.
'''

import pytest

from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.messageAgent import MessageAgent
from sam.serverController.vnfController.sourceAllocator import SourceAllocator
from sam.test.testBase import TestBase


class TestVNFAddFW(TestBase):
    @pytest.fixture(scope="function")
    def setup_sourceAllocator(self):
        # setup
        logConfigur = LoggerConfigurator(__name__, './log',
            'tester.log', level='debug')
        self.logger = logConfigur.getLogger()
        self._messageAgent = MessageAgent(self.logger)

        self.sA = SourceAllocator(1, 1000, 0)

        yield
        # teardown

    def test_sourceAllocator(self, setup_sourceAllocator):
        # exercise
        res = self.sA.allocateSpecificSource(200, 1)
        # verifiy
        assert res == 200
        assert self.sA._unallocatedList == [[0,199],[201,1000]]

        # exercise
        res = self.sA.allocateSpecificSource(200, 1)
        # verifiy
        assert res == -1
        assert self.sA._unallocatedList == [[0,199],[201,1000]]

        # exercise
        res = self.sA.allocateSpecificSource(100, 1)
        # verifiy
        assert res == 100
        assert self.sA._unallocatedList == [[0,99],[101,199],[201,1000]]

        # exercise
        res = self.sA.allocateSpecificSource(199, 1)
        # verifiy
        assert res == 199
        assert self.sA._unallocatedList == [[0,99],[101,198],[201,1000]]

        # exercise
        res = self.sA.allocateSpecificSource(101, 198-101+1)
        # verifiy
        assert res == 101
        assert self.sA._unallocatedList == [[0,99],[201,1000]]

        # exercise
        res = self.sA.allocateSpecificSource(5, 5)
        # verifiy
        assert res == 5
        assert self.sA._unallocatedList == [[0,4],[10,99],[201,1000]]