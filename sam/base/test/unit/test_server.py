#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging

import pytest

from sam.base.server import Server, SERVER_TYPE_NORMAL

MANUAL_TEST = True


class TestServerClass(object):
    banList = """
    setServerID
    getServerID
    getIfSet
    printIfSet
    getControlNICMac
    getDatapathNICMac
    getControlNICIP
    _getIPList
    printCpuUtil
    updateResource
    """

    @classmethod
    def setup_class(cls):
        """ setup any state specific to the execution of the given class (which
        usually contains tests).
        """
        controlIfName = "eno1"
        datapathIfIP = "2.2.0.36"
        cls.server = Server(controlIfName, datapathIfIP, SERVER_TYPE_NORMAL)

    @classmethod
    def teardown_class(cls):
        """ teardown any state that was previously setup with a call to
        setup_class.
        """

    # @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_updateControlNICMAC(self):
        self.server.updateControlNICMAC()
        assert self.server._serverControlNICMAC == "b8:ca:3a:65:f7:f8"

    # @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_updateDataPathNICMAC(self):
        self.server.updateDataPathNICMAC()
        assert self.server._serverDatapathNICMAC == "b4:96:91:b2:9f:98"

    # @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_updateIfSet(self):
        self.server.updateIfSet()
        assert self.server._ifSet["eno1"]["MAC"] == "b8:ca:3a:65:f7:f8"
        assert self.server._ifSet["eno1"]["IP"] == ["192.168.8.17"]

    # @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_getHwAddrInDPDK(self):
        result = self.server._getHwAddrInDPDK()
        assert result == "b4:96:91:b2:9f:98"

    # @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_getHwAddrInKernel(self):
        result = self.server._getHwAddrInKernel("eno1")
        assert result == "b8:ca:3a:65:f7:f8"

    # @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_updateSocketNum(self):
        self.server._updateSocketNum()
        assert self.server._socketNum == 2

    # @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_updateCoreSocketDistribution(self):
        self.server._updateSocketNum()
        self.server._updateCoreSocketDistribution()
        assert self.server._coreSocketDistribution == [20, 20]

    # @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_updateNUMANum(self):
        self.server._updateNUMANum()
        assert self.server._numaNum == 2

    # @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_getSMPCoresNum(self):
        rv = self.server._getSMPCoresNum()
        assert rv == 40

    # @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_updateCoreNUMADistribution(self):
        self.server._updateSocketNum()
        self.server._updateCoreNUMADistribution()
        assert self.server._coreNUMADistribution == [[0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38], [1,3,5,7,9,11,13,15,17,19,21,23,25,27,29,31,33,35,37,39]]

    # @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_updateCpuUtil(self):
        self.server._updateCpuUtil()
        assert self.server._coreUtilization[0] >= 0.0 and self.server._coreUtilization[0] <= 100.0

    # @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_isSMP(self):
        rv = self.server._isSMP()
        assert rv == False

    # @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_updateHugepagesTotal(self):
        self.server._updateSocketNum()
        self.server._updateHugepagesTotal()
        assert self.server._hugepagesTotal == [6, 6]

    # @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_updateHugepagesFree(self):
        self.server._updateSocketNum()
        self.server._updateHugepagesFree()
        assert self.server._hugepagesFree == [3, 4]

    # @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_updateHugepagesSize(self):
        self.server._updateHugepagesSize()
        assert self.server._hugepageSize == 1048576

    # @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_updateMemAccessMode(self):
        self.server._updateMemAccessMode()
        assert self.server._memoryAccessMode == "NUMA"

