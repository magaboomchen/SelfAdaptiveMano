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
from sam.base.socketConverter import *
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.orchestration.algorithms.multiLayerGraph import *


class PartialLP(object):
    def __init__(self, dib, requestList, requestForwardingPathSet):
        self._dib = dib
        self.requestList = requestList
        self.requestForwardingPathSet = requestForwardingPathSet
        self._sc = SocketConverter()

        logConfigur = LoggerConfigurator(__name__,
            './log',
            'PartialLP.log', level='warning')
        self.logger = logConfigur.getLogger()

    def mapSFCI(self):
        self.logger.info("PartialLP mapSFCI")
        self._init()
        self._genVariablesAndConsts()
        self._trans2LPAndSolve()

    def _init(self):
        self.switches = {}
        self.requestVnf = {}
        self.phsicalLink = gp.tuplelist()
        self.virtualLink = {}
        self.requestIngSwitchID = {}
        self.requestEgSwitchID = {}

    def _genVariablesAndConsts(self):
        # p = (sp, bp, tp, Xp, lp), {(sp,bp,tp): [Xp,lp]}
        # f^{p}_{i,j,u,v}
        # f^{p}_{0,mr,u,sr}
        self._genPhysicalLinksVar() # C_{u,v}
        self._genVirtualLinkVar()
        # A^r_{i,w}
        self._genSwitchesVar()  # C_w
        self._genVnfVar()
        # l_r
        self._genRequestLoad()
        # s_r, t_r
        self._genRequestIngAndEg()

    def _trans2LPAndSolve(self):
        try:
            # Clear environment
            disposeDefaultEnv()

            # Create optimization model
            m = gp.Model('PartialLP')

            # Create continuous variables
            help(Model.addVars)

        except GurobiError:
            self.logger.error('Error reported')

        finally:
            # clean up gruobi environment
            disposeDefaultEnv()
