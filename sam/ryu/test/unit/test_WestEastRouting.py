#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging

logging.basicConfig(level=logging.INFO)


class TestWestEastRoutingClass(object):
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
