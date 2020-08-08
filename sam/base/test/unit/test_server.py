import pytest
from sam.base.server import *

MANUAL_TEST = True

class TestServerClass(object):
    banList = """
    updateServerID
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
    def test_updateCpuCount(self):
        self.server._updateCpuCount()
        assert self.server._CPUNum == 12

    def test_updateCpuUtil(self):
        self.server._updateCpuUtil()
        assert self.server._CPUUtil >= 0.0 and self.server._CPUUtil <= 100.0

    @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_updateHugepagesTotal(self):
        self.server._updateHugepagesTotal()
        assert self.server._hugepagesTotal == 0

    @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_updateHugepagesFree(self):
        self.server._updateHugepagesFree()
        assert self.server._hugepagesFree == 0

    @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_updateHugepagesSize(self):
        self.server._updateHugepagesSize()
        assert self.server._hugepageSize == 2048