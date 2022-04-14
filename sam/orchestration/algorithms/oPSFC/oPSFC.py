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
from sam.orchestration.algorithms.oPSFC.originalPartialLP import *
from sam.orchestration.algorithms.oPSFC.opRandomizedRoundingAlgorithm import *
from sam.orchestration.algorithms.base.multiLayerGraph import *


class OPSFC(object):
    def __init__(self, dib, requestBatchList):
        self._dib = dib
        self.requestList = copy.deepcopy(requestBatchList)
        self._sc = SocketConverter()

        logConfigur = LoggerConfigurator(__name__, './log',
            'OPSFC.log', level='debug')
        self.logger = logConfigur.getLogger()

    def mapSFCI(self):
        self.logger.info("OPSFC mapSFCI")

        # LP
        self.opLP = OriginalPartialLP(self._dib, self.requestList)
        self.opLP.mapSFCI()

        # OP-RRA
        self.rra = OPRandomizedRoundingAlgorithm(
            self._dib, self.requestList, self.opLP)
        self.rra.mapSFCI()

        return self.rra.forwardingPathSetsDict
