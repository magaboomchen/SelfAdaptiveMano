#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
 dedicated protection sfc mapping
[2018][icc]Resource Requirements for
Reliable Service Function Chaining
'''

import copy

import numpy as np
import gurobipy as gp
from gurobipy import GRB
from gurobipy import *

from sam.base.path import *
from sam.base.server import *
from sam.base.messageAgent import *
from sam.base.socketConverter import *
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.orchestration.algorithms.dpSFC.nfvCGDP import *
from sam.orchestration.algorithms.dpSFC.nfvDPPP import *


class DPSFC(object):
    def __init__(self, dib, requestList):
        self._dib = dib
        self.requestList = requestList
        self.nfvCGDP = NFVCGDedicatedProtection(self._dib, self.requestList)
        self.nfvDPPP = NFVDPPricingProblem(self._dib, self.requestList)

        logConfigur = LoggerConfigurator(__name__,
            './log', 'DPSFC.log', level='warning')
        self.logger = logConfigur.getLogger()

    def mapSFCI(self):
        # https://www.gurobi.com/wp-content/plugins/hd_documentations/documentation/9.1/refman.pdf
        # 存储，计算多个model
        self.logger.info("DPSFC mapSFCI")
        self.nfvCGDP.initRMP()

        while True:
            self.nfvCGDP.solve()
            dualVars = self.nfvCGDP.getDualVariables()
            self.nfvDPPP.initPPs(dualVars)   # model.Dispose() ?
            self.nfvDPPP.solveAllPPs()
            if self.nfvDPPP.hasBetterConfigurations():  # reduced cost < 0
                configurations = self.nfvDPPP.getConfigurations()
                self.nfvCGDP.addConfigurations(configurations)
            else:
                break

        self.nfvCGDP.transRMP2ILP()
        self.nfvCGDP.solve()

        solution = self.nfvCGDP.getSolution()
        return self._transSolution2RequestForwardingPathSet(solution)

    def _transSolution2RequestForwardingPathSet(self, solution):
        self.nfvCGDP.logSolution()
        return None
