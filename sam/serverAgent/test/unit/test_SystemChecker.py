#!/usr/bin/python
# -*- coding: UTF-8 -*-

import pytest
from sam.serverAgent.systemChecker import *
import subprocess

class TestSystemCheckerClass(object):
    banList = """
    checkUserPermission
    checkRTE_SDK
    """

    @classmethod
    def setup_class(cls):
        """ setup any state specific to the execution of the given class (which
        usually contains tests).
        """
        cls.sc = SystemChecker()

    @classmethod
    def teardown_class(cls):
        """ teardown any state that was previously setup with a call to
        setup_class.
        """