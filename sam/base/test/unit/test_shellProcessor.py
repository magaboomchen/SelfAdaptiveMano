#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging
import os
import subprocess

import pytest

from sam.base.shellProcessor import ShellProcessor
from sam.base.test.unit.fixtures import tmpScript
from sam.orchestration import orchestrator

MANUAL_TEST = True


class TestShellProcessorClass(object):
    def setup_method(self, method):
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """
        self.sP = ShellProcessor()

    def teardown_method(self, method):
        """ teardown any state that was previously setup with a setup_method
        call.
        """
        self.sP = None

    def test_isProcessRun(self):
        assert self.sP.isProcessRun("bioset") == True

    @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_runProcess(self):
        pass

    @pytest.mark.skipif(MANUAL_TEST == True, reason='Manual testing is required')
    def test_killProcess(self):
        pass
    
    def test_runPythonScript(self):
        filePath = tmpScript.__file__
        self.sP.runPythonScript(filePath)
        out_bytes = subprocess.check_output(
            ["ps -ef | grep tmpScript.py"], shell=True)
        out_bytes = str(out_bytes)
        assert out_bytes.count("tmpScript") >= 3

    def test_isPythonScriptRun(self):
        filePath = tmpScript.__file__
        subprocess.Popen(
            ["python " + filePath], shell=True)
        assert self.sP.isPythonScriptRun("tmpScript.py") == True

    def test_killPythonScript(self):
        filePath = tmpScript.__file__
        self.sP.runPythonScript(filePath)
        self.sP.killPythonScript("tmpScript.py")
        out_bytes = subprocess.check_output(
            ["ps -ef | grep tmpScript.py"], shell=True)
        out_bytes = str(out_bytes)
        assert out_bytes.count("tmpScript.py") == 2

    def test_getPythonScriptProcessPid(self):
        orchestratorFilePath = os.path.abspath(orchestrator.__file__)
        cmdline = "python {0} -name 0-19 -p 20 -minPIdx 0 -maxPIdx 19".format(orchestratorFilePath)
        pId = self.sP.getPythonScriptProcessPid(cmdline)
        print("pId is {0}".format(pId))
        assert 2 == 2