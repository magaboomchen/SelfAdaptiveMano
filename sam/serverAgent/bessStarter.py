#!/usr/bin/python
# -*- coding: UTF-8 -*-

import subprocess

import psutil

from sam.base.shellProcessor import ShellProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.serverAgent.dpdkConfigurator import DPDKConfigurator

class BessStarter(object):
    def __init__(self, grpcUrl, NICPCIAddress):
        logConfigur = LoggerConfigurator(__name__, './log',
            'bessStarter.log', level='info')
        self.logger = logConfigur.getLogger()
        self.logger.info('Init bessd')

        self.NICPCIAddress = NICPCIAddress
        self.grpcUrl = grpcUrl

    def startBESSD(self):
        if not self.isBessdRun():
            DPDKConfigurator(self.NICPCIAddress)
            out_bytes = subprocess.check_output(["sudo -E $RTE_SDK/../../core/bessd -k --grpc_url="+str(self.grpcUrl)],shell=True)
            self.logger.info("Start bessd.")

    def isBessdRun(self):
        for p in psutil.process_iter(attrs=['pid', 'name']):
            if 'bessd' in p.info['name']:
                self.logger.info("bessd has already running.")
                return True
        return False
    
    def killBessd(self):
        self.logger.info("Trying to kill bessd.")
        if self.isBessdRun():
            self.sP = ShellProcessor()
            self.sP.runShellCommand("sudo killall bessd")
        else:
            self.logger.info("bessd already been killed.")