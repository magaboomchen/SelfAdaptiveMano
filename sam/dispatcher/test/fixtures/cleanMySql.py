#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
if sys.version > '3':
    import queue as Queue
else:
    import Queue

from sam.base.messageAgent import *
from sam.base.request import Request, Reply
from sam.orchestration.argParser import ArgParser
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.measurement.dcnInfoBaseMaintainer import *
from sam.orchestration.oDcnInfoRetriever import *
from sam.orchestration.oSFCAdder import *
from sam.orchestration.oSFCDeleter import *
from sam.orchestration.oConfig import *
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer


class MySqlCleaner(object):
    def __init__(self):
        logConfigur = LoggerConfigurator(__name__, './log',
            'MySqlCleaner.log', level='debug')
        self.logger = logConfigur.getLogger()

        self._oib = OrchInfoBaseMaintainer("localhost", "dbAgent", "123")
        self._oib.cleanTable()

if __name__ == "__main__":
    msc = MySqlCleaner()
