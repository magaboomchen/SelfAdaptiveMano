#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
import sys
import subprocess

from sam.base.loggerConfigurator import LoggerConfigurator


class SystemChecker(object):
    def __init__(self):
        logConfigur = LoggerConfigurator(__name__, './log',
            'systemChecker.log', level='info')
        self.logger = logConfigur.getLogger()
        self.checkUserPermission()
        self.checkRTE_SDK()

    def checkUserPermission(self):
        if 'SUDO_UID' in os.environ.keys():
            self.logger.warning("Check user permission, please don't use sudo or root.")
            sys.exit(1)

    def checkRTE_SDK(self):
        # check whether $RTE_SDK is available
        out_bytes = subprocess.check_output(['echo $RTE_SDK'], shell=True)
        out_bytes = str(out_bytes)
        if len(out_bytes) == 1:
            self.logger.error("Path environment $RTE_SDK is not defined, please define it as the path of dpdk directory.")
            exit(1)