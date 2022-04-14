#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
 dedicated protection sfc mapping
[2018][icc]Resource Requirements for
Reliable Service Function Chaining

https://www.gurobi.com/wp-content/plugins/hd_documentations/documentation/9.1/refman.pdf
'''

import copy
import time

import numpy as np
import gurobipy as gp
from gurobipy import GRB
from gurobipy import *

from sam.base.path import *
from sam.base.server import *
from sam.base.messageAgent import *
from sam.base.socketConverter import SocketConverter, BCAST_MAC
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.orchestration.algorithms.dpSFCCG.nfvCGDP import *
from sam.orchestration.algorithms.dpSFCCG.nfvDPPP import *


TIME_LIMIT = 180

class DPSFCCG(object):
    def __init__(self, dib, requestList):
        self._dib = dib
        self.requestList = requestList
        self.nfvCGDP = NFVCGDedicatedProtection(self._dib, self.requestList)
        self.nfvDPPP = NFVDPPricingProblem(self._dib, self.requestList)

        logConfigur = LoggerConfigurator(__name__,
            './log', 'DPSFC.log', level='debug')
        self.logger = logConfigur.getLogger()

    def mapSFCI(self):
        self.logger.info("DPSFC mapSFCI")

        self.starttime = self.recordTime()

        self.nfvCGDP.initRMP()
        while True:
            self.nfvCGDP.updateRMP()
            self.nfvCGDP.solve()
            dualVars = self.nfvCGDP.getDualVariables()
            self.nfvDPPP.initPPs(dualVars)   # model.Dispose() ?
            self.nfvDPPP.solveAllPPs()
            if self.nfvDPPP.hasBetterConfigurations():  # reduced cost < 0
                self.logger.debug("has better configuration")
                configurations = self.nfvDPPP.getConfigurations()
                if self.nfvCGDP.hasNewConfigurations(configurations):
                    self.nfvCGDP.addConfigurations(configurations)
                else:
                    # We doubt the validity of cg model in that paper.
                    # There is a high probability that pricing problems can't 
                    # generate vaild primary/backup path because each 
                    # pricing problem doesn't consider the 
                    # resource consumption by other sfc requests.
                    # As a result, a shortest path will be generated
                    # for each pricing problem.
                    self.logger.warning("No new configurations!")
                    break
            else:
                break

            self.endtime = self.recordTime()
            if self._isTimeExceed():
                break

        self.nfvCGDP.transRMP2ILP()
        self.nfvCGDP.solve()

        forwardingPathSetsDict \
            = self.nfvCGDP.getForwardingPathSetsDict()

        self.nfvDPPP.garbageCollector()
        self.nfvCGDP.garbageCollector()

        return forwardingPathSetsDict

    def recordTime(self):
        return time.time()

    def _isTimeExceed(self):
        timeUsage = self.endtime - self.starttime
        return timeUsage > TIME_LIMIT
