#!/usr/bin/python
# -*- coding: UTF-8 -*-

import copy
import json

from sam.base.loggerConfigurator import LoggerConfigurator
from sam.ryu.ribMaintainerBase import RIBMaintainerBase
from sam.base.socketConverter import *

# TODO: test


class NotViaNATIBMaintainer(RIBMaintainerBase):
    def __init__(self):
        super(NotViaNATIBMaintainer, self).__init__()
        self.groupIDSets = {}
        self._sc = SocketConverter()

        logConfigur = LoggerConfigurator(__name__, './log',
            'NotViaNATIBMaintainer.log', level='debug')
        self.logger = logConfigur.getLogger()

