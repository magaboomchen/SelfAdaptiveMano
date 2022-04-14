#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
original sfc mapping
[2018][globecom]Partial Rerouting for High-Availability and
Low-Cost Service Function Chain
'''

import copy

import numpy as np
import gurobipy as gp
from gurobipy import GRB
from gurobipy import *

from sam.base.path import *
from sam.base.server import *
from sam.base.messageAgent import *
from sam.base.socketConverter import SocketConverter, BCAST_MAC
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.orchestration.algorithms.pSFC.partialLP import *
from sam.orchestration.algorithms.pSFC.pRandomizedRoundingAlgorithm import *
from sam.orchestration.algorithms.base.multiLayerGraph import *


class PSFC(object):
    # RYU部署初始/备份路径，用不同优先级表示。
    # adaptive模块根据测量结果，触发SFF的相应表项的优先级变更即可。

    def __init__(self, dib, requestBatchList, forwardingPathSetsDict):
        self._dib = dib
        self.requestList = copy.deepcopy(requestBatchList)
        self.forwardingPathSetsDict = forwardingPathSetsDict
        self._sc = SocketConverter()

        logConfigur = LoggerConfigurator(__name__, './log',
            'PSFC.log', level='debug')
        self.logger = logConfigur.getLogger()

    def mapSFCI(self):
        self.logger.info("PSFC mapSFCI")

        # LP
        self.pLP = PartialLP(self._dib, self.requestList, self.forwardingPathSetsDict)
        self.pLP.mapSFCI()

        # P-RRA
        self.rra = PRandomizedRoundingAlgorithm(
            self._dib, self.requestList, self.pLP, self.forwardingPathSetsDict)
        self.rra.mapSFCI()
        self.dibDict = self.rra.getDibDict()

        self.logger.debug(
            "forwardingPathSetsDict:{0}".format(
                self.forwardingPathSetsDict))

        return self.rra.forwardingPathSetsDict
