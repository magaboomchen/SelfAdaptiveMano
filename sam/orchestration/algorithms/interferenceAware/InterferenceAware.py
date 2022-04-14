#!/usr/bin/python
# -*- coding: UTF-8 -*-

import copy
import time

import numpy as np

from sam.base.path import *
from sam.base.server import *
from sam.base.messageAgent import *
from sam.base.socketConverter import SocketConverter, BCAST_MAC
from sam.base.loggerConfigurator import LoggerConfigurator


class InterferenceAware(object):
    def __init__(self, dib, requestList):
        self._dib = dib
        self.requestList = requestList

        logConfigur = LoggerConfigurator(__name__,
            './log', 'InterferenceAware.log', level='debug')
        self.logger = logConfigur.getLogger()

    def mapSFCI(self):
        self.logger.info("InterferenceAware mapSFCI")
        # implement your mapping algorithm here
        pass

        # If you want to calculate sfc path, here is the format of forwardingPathSetsDict
        # self.forwardingPathSetsDict[rIndex] = ForwardingPathSet(
        #     primaryForwardingPath,
        #     mappingType=MAPPING_TYPE_INTERFERENCE,
        #     backupForwardingPath=None)

        return forwardingPathSetsDict
