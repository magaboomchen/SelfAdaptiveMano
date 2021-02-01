#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.socketConverter import *
from sam.base.xibMaintainer import XInfoBaseMaintainer
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.ryu.uibMaintainer import UIBMaintainer

# TODO: test


class DPSFCIBMaintainer(UIBMaintainer):
    def __init__(self, *args, **kwargs):
        super(DPSFCIBMaintainer, self).__init__(*args, **kwargs)
        logConfigur = LoggerConfigurator(__name__, './log',
            'DPSFCIBMaintainer.log', level='debug')
        self.logger = logConfigur.getLogger()

