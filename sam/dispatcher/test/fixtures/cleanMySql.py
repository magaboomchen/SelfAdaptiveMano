#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.loggerConfigurator import LoggerConfigurator
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer


class MySqlCleaner(object):
    def __init__(self):
        logConfigur = LoggerConfigurator(__name__, './log',
            'MySqlCleaner.log', level='debug')
        self.logger = logConfigur.getLogger()

        self._oib = OrchInfoBaseMaintainer("localhost", "dbAgent", "123")
        self._oib.dropTable()

if __name__ == "__main__":
    msc = MySqlCleaner()
