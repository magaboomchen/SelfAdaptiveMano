#!/usr/bin/python
# -*- coding: UTF-8 -*-

import subprocess
import logging

import psutil

class BessStarter(object):
    def __init__(self, grpcUrl):
        logging.info('Init bessd')
        self.grpcUrl = grpcUrl
        if self.isBessdRun() == 0:
            self.startBESSD()

    def startBESSD(self):
        out_bytes = subprocess.check_output(["sudo -E $RTE_SDK/../../core/bessd -k --grpc_url="+str(self.grpcUrl)],shell=True)
        logging.info("Start bessd.")

    def isBessdRun(self):
        for p in psutil.process_iter(attrs=['pid', 'name']):
            if 'bessd' in p.info['name']:
                logging.info("bessd has already running.")
                return True
        return False