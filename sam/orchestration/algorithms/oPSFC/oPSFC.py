#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
original sfc mapping
[2018][globecom]Partial Rerouting for High-Availability and
Low-Cost Service Function Chain
'''

import copy

from sam.base.socketConverter import SocketConverter
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.orchestration.algorithms.oPSFC.originalPartialLP import OriginalPartialLP
from sam.orchestration.algorithms.oPSFC.opRandomizedRoundingAlgorithm import OPRandomizedRoundingAlgorithm


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
