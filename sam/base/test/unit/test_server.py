#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging

import pytest

from sam.base.server import Server, SERVER_TYPE_NORMAL

MANUAL_TEST = True

logging.basicConfig(level=logging.INFO)


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

    @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_updateControlNICMAC(self):
        self.server.updateControlNICMAC()
        assert self.server._serverControlNICMAC == "18:66:da:86:4c:15"

    @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_updateDataPathNICMAC(self):
        self.server.updateDataPathNICMAC()
        assert self.server._serverDatapathNICMAC == "18:66:da:86:4c:15"

    @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_updateIfSet(self):
        self.server.updateIfSet()
        assert self.server._ifSet["eno1"]["MAC"] == "18:66:da:86:4c:15"
        assert self.server._ifSet["eno1"]["IP"] == "2.2.0.163"

    @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_getHwAddrInDPDK(self):
        result = self.server._getHwAddrInDPDK()
        assert result == "18:66:da:86:4c:15"

    @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_getHwAddrInKernel(self):
        result = self.server._getHwAddrInKernel("eno1")
        assert result == "18:66:da:86:4c:15"

    @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_updateSocketNum(self):
        self.server._updateSocketNum()
        assert self.server._socketNum == 2

    @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_updateCoreSocketDistribution(self):
        self.server._updateSocketNum()
        self.server._updateCoreSocketDistribution()
        assert self.server._coreSocketDistribution == [12, 12]

    @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_updateNUMANum(self):
        self.server._updateNUMANum()
        assert self.server._numaNum == 2

    # @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_getSMPCoresNum(self):
        rv = self.server._getSMPCoresNum()
        assert rv == 12

    @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_updateCoreNUMADistribution(self):
        self.server._updateSocketNum()
        self.server._updateCoreNUMADistribution()
        assert self.server._coreNUMADistribution == [12,12]

    @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_updateCpuUtil(self):
        self.server._updateCpuUtil()
        assert self.server._coreUtilization[0] >= 0.0 and self.server._coreUtilization[0] <= 100.0

    @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_isSMP(self):
        rv = self.server._isSMP()
        assert rv

    @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_updateHugepagesTotal(self):
        self.server._updateSocketNum()
        self.server._updateHugepagesTotal()
        assert self.server._hugepagesTotal == 0

    @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_updateHugepagesFree(self):
        self.server._updateSocketNum()
        self.server._updateHugepagesFree()
        assert self.server._hugepagesFree == 0

    @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_updateHugepagesSize(self):
        self.server._updateHugepagesSize()
        assert self.server._hugepageSize == 2048

    # @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_updateMemAccessMode(self):
        self.server._updateMemAccessMode()
        assert self.server._memoryAccessMode == "NUMA"

