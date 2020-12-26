#!/usr/bin/python
# -*- coding: UTF-8 -*-

from gurobipy import *

from sam.base.loggerConfigurator import LoggerConfigurator


class PSFC(object):
    def __init__(self, dib, requestBatchQueue, mapResults):
        self._dib = dib
        self.requestBatchQueue = requestBatchQueue

        logConfigur = LoggerConfigurator(__name__, './log',
            'PSFC.log', level='debug')
        self.logger = logConfigur.getLogger()

    def init(self):
        pass

    def mapSFCI(self):
        self.logger.info("mapSFCI")
        self.init()
        self.pSFC()

        # TODO
        mapResults = None

        return mapResults

    def pSFC(self):
        self._trans2MILP()
        self._solveMILP()
        self._randomizedRoundingAlgorithm()
        # 生成的结果中，备份路径字典写成：(1,2,"*")来保护SFF即可。
        # RYU部署初始/备份路径，用不同优先级表示。
        # adaptive模块根据测量结果，触发SFF的相应表项的优先级变更即可。
        return None

    def _trans2MILP(self):
        pass
    
    def _solveMILP(self):
        pass

    def _randomizedRoundingAlgorithm(self):
        pass


if __name__ == "__main__":
    pass
