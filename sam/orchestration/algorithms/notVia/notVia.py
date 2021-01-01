#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.loggerConfigurator import LoggerConfigurator


class NotVia(object):
    def __init__(self, dib, requestBatchQueue, mapResults):
        self._dib = dib
        self.requestBatchQueue = requestBatchQueue
        self.mapResults = mapResults

        logConfigur = LoggerConfigurator(__name__, './log',
            'NotVia.log', level='debug')
        self.logger = logConfigur.getLogger()

    def init(self):
        pass

    def mapSFCI(self):
        self.logger.info("mapSFCI")
        self.init()
        self.notVia()

        # TODO
        mapResults = None

        return mapResults

    def notVia(self):
        pass

if __name__ == "__main__":
    pass
