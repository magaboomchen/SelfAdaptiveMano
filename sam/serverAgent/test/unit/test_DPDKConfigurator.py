#!/usr/bin/python
# -*- coding: UTF-8 -*-

import subprocess

from sam.serverAgent.dpdkConfigurator import DPDKConfigurator, \
    UNBIND, BIND_IGB_UIO


class TestDPDKConfiguratorClass(object):
    banList = """
    _getNICStatus
    _configDPDK
    """

    @classmethod
    def setup_class(cls):
        """ setup any state specific to the execution of the given class (which
        usually contains tests).
        """
        cls.dc = DPDKConfigurator("0000:00:08.0")

    @classmethod
    def teardown_class(cls):
        """ teardown any state that was previously setup with a call to
        setup_class.
        """

    def test_insertIGB_UIO(self):
        self.dc.insertIGB_UIO()
        out_bytes = subprocess.check_output(['lsmod'],shell=True)
        out_bytes = str(out_bytes)
        assert out_bytes.find('igb_uio') != -1

    def test_bindNIC(self):
        if self.dc.getNICStatus() != UNBIND:
            self.dc.unbindNIC()
            assert self.dc.getNICStatus() == UNBIND
        self.dc.bindNIC()
        assert self.dc.getNICStatus() == BIND_IGB_UIO

    def test_unbindNIC(self):
        if self.dc.getNICStatus() == UNBIND:
            self.dc.bindNID()
            assert self.dc.getNICStatus() == BIND_IGB_UIO
        self.dc.unbindNIC()
        assert self.dc.getNICStatus() == UNBIND