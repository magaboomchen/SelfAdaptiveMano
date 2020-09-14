#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging

import pytest

from sam.base.shellProcessor import *

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
        filePath = "~/HaoChen/Project/SelfAdaptiveMano/sam/base/test/unit/fixtures/tmpScript.py"
        self.sp.runPythonScript(filePath)
        out_bytes = subprocess.check_output(
            ["ps -ef | grep tmpScript.py"], shell=True)
        assert out_bytes.count("tmpScript") >= 3

    def test_isPythonScriptRun(self):
        filePath = "~/HaoChen/Project/SelfAdaptiveMano/sam/base/test/unit/fixtures/tmpScript.py"
        subprocess.Popen(
            ["python " + filePath], shell=True)
        assert self.sp.isPythonScriptRun("tmpScript.py") == True

    def test_killPythonScript(self):
        filePath = "~/HaoChen/Project/SelfAdaptiveMano/sam/base/test/unit/fixtures/tmpScript.py"
        self.sp.runPythonScript(filePath)
        self.sp.killPythonScript("tmpScript.py")
        out_bytes = subprocess.check_output(
            ["ps -ef | grep tmpScript.py"], shell=True)
        assert out_bytes.count("tmpScript.py") == 2