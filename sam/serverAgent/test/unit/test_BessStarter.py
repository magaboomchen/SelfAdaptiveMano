#!/usr/bin/python
# -*- coding: UTF-8 -*-

import psutil
import logging
import subprocess

from sam.serverAgent.bessStarter import BessStarter


class TestBessStarterClass(object):
    @classmethod
    def setup_class(cls):
        """ setup any state specific to the execution of the given class (which
        usually contains tests).
        """
        cls.bs = BessStarter()

    @classmethod
    def teardown_class(cls):
        """ teardown any state that was previously setup with a call to
        setup_class.
        """

    def test_startBESSD(self):
        self.bs.startBESSD()

        out_bytes = subprocess.check_output(["ps -ef | grep bessd"],shell=True)
        out_bytes = str(out_bytes)
        assert out_bytes.count("bessd") == 3

    def test_isBessdRun(self):
        for p in psutil.process_iter(attrs=['pid', 'name']):
            if 'bessd' in p.info['name']:
                pid = int(p.info['pid'])
                out_bytes = subprocess.check_output(["sudo kill "+str(pid)],shell=True)
        assert self.bs.isBessdRun() == 0

        self.bs.startBESSD()
        assert self.bs.isBessdRun() == 1