#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging

from sam.ryu.L2 import L2


class TestL2Class(object):
    @classmethod
    def setup_class(cls):
        """ setup any state specific to the execution of the given class (which
        usually contains tests).
        """

    @classmethod
    def teardown_class(cls):
        """ teardown any state that was previously setup with a call to
        setup_class.
        """