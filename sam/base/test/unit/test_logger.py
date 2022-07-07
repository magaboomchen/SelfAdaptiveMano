#!/usr/bin/python
# -*- coding: UTF-8 -*-

import time
import logging
from sam.base.loggerConfigurator import LoggerConfigurator

from sam.test.testBase import TestBase
from sam.base.messageAgent import MessageAgent, SAMMessage

MANUAL_TEST = True

logging.basicConfig(level=logging.DEBUG)


class TestLoggerClass(TestBase):
    def setup_method(self, method):
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """

        logConfigur = LoggerConfigurator(__name__, './log',
            'Logger.log', level='info')
        self.logger = logConfigur.getLogger()

    def teardown_method(self, method):
        """ teardown any state that was previously setup with a setup_method
        call.
        """

    def test_requestMsgByRPC(self):
        self.logger.debug("Hello")
        self.logger.info("Hello")
        self.logger.warning("Hello")
        self.logger.error("Hello")
        assert True
