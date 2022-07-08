#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.socketConverter import SocketConverter
from sam.base.loggerConfigurator import LoggerConfigurator


class DashboardTestBase(object):
    logConfigur = LoggerConfigurator(__name__, './log',
        'dashboardTest.log', level='debug')
    logger = logConfigur.getLogger()
    _sc = SocketConverter()