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
from gurobipy import *
from gurobipy import GRB

from sam.base.path import *
from sam.base.server import *
from sam.base.messageAgent import *
from sam.base.socketConverter import *
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.serverController.serverManager.serverManager import *
from sam.orchestration.algorithms.multiLayerGraph import *


class PRandomizedRoundingAlgorithm(object):
    def __init__(self, dib, requestList, opLP, requestForwardingPathSet):
        self._dib = dib
        self.requestList = requestList
        self.opLP = opLP
        self.requestForwardingPathSet = requestForwardingPathSet
        self._sc = SocketConverter()

        logConfigur = LoggerConfigurator(__name__, './log',
            'OP-RRA.log', level='debug')
        self.logger = logConfigur.getLogger()

    def mapSFCI(self):
        self.logger.info("PRandomizedRoundingAlgorithm mapSFCI")
        # self.init()
        # self.randomizedRoundingAlgorithm()
