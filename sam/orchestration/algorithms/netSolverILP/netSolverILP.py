#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
 dedicated protection sfc mapping
[2018][icc]Resource Requirements for
Reliable Service Function Chaining

https://www.gurobi.com/wp-content/plugins/hd_documentations/documentation/9.1/refman.pdf
'''

import time

from sam.base.loggerConfigurator import LoggerConfigurator
from sam.orchestration.algorithms.netSolverILP.ilpModel import ILPModel, INITIAL_PATH_PER_REQUEST_NUM


TIME_LIMIT = 180

class NetSolverILP(object):
    def __init__(self, dib, requestList, topoType="fat-tree"):
        self._dib = dib
        self.requestList = requestList
        self.topoType = topoType
        self.ilpModel = ILPModel(self._dib, self.requestList, self.topoType)

        logConfigur = LoggerConfigurator(__name__,
            './log', 'NetSolverILP.log', level='debug')
        self.logger = logConfigur.getLogger()

        self.zoneName = self.requestList[0].attributes['zone']

    def mapSFCI(self, podNum, minPodIdx, maxPodIdx):
        self.logger.info("NetSolverILP mapSFCI")

        self.starttime = self.recordTime()

        self.ilpModel.loadFatTreeArg(podNum, minPodIdx, maxPodIdx)
        self.ilpModel.initModel()
        self.ilpModel.updateModel()
        self.ilpModel.solve()

        forwardingPathSetsDict \
            = self.ilpModel.getForwardingPathSetsDict()

        self.ilpModel._updateResource()

        self.ilpModel.garbageCollector()

        return forwardingPathSetsDict

    def recordTime(self):
        return time.time()

    def _isTimeExceed(self):
        timeUsage = self.endtime - self.starttime
        return timeUsage > TIME_LIMIT
