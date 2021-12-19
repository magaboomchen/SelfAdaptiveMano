#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging

import pytest

from sam.base.shellProcessor import *
from sam.base.test.unit.fixtures import tmpScript

MANUAL_TEST = True

logging.basicConfig(level=logging.INFO)

class TestShellProcessorClass(object):
    def setup_method(self, method):
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """
        self.sp = ShellProcessor()

    def teardown_method(self, method):
        """ teardown any state that was previously setup with a setup_method
        call.
        """
        self.sp = None

    def test_isProcessRun(self):
        assert self.sp.isProcessRun("bioset") == True

    @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_runProcess(self):
        pass

    @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_killProcess(self):
        pass
    
    def test_runPythonScript(self):
        filePath = tmpScript.__file__
        self.sp.runPythonScript(filePath)
        out_bytes = subprocess.check_output(
            ["ps -ef | grep tmpScript.py"], shell=True)
        assert out_bytes.count("tmpScript") >= 3

    def test_isPythonScriptRun(self):
        filePath = tmpScript.__file__
        subprocess.Popen(
            ["python " + filePath], shell=True)
        assert self.sp.isPythonScriptRun("tmpScript.py") == True

    def test_killPythonScript(self):
        filePath = tmpScript.__file__
        self.sp.runPythonScript(filePath)
        self.sp.killPythonScript("tmpScript.py")
        out_bytes = subprocess.check_output(
            ["ps -ef | grep tmpScript.py"], shell=True)
        assert out_bytes.count("tmpScript.py") == 2

    def test_getPythonScriptProcessPid(self):
        cmdline = "python /home/smith/Projects/SelfAdaptiveMano/sam/orchestration/orchestrator.py -name 0-19 -p 20 -minPIdx 0 -maxPIdx 19"
        pId = self.sP.getPythonScriptProcessPid(cmdline)
        print("pId is {0}".format(pId))
        assert 2 == 2
