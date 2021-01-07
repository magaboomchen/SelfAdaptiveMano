#!/usr/bin/python
# -*- coding: UTF-8 -*-

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


class MMLPSFC(object):
    def __init__(self, dib, requestList):
        self._dib = dib
        self.requestList = requestList

        logConfigur = LoggerConfigurator(__name__,
            './log', 'MMLPSFC.log', level='warning')
        self.logger = logConfigur.getLogger()

    def mapSFCI(self):
        self.logger.info("MMLPSFC mapSFCI")
