#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging
from sam.base.loggerConfigurator import LoggerConfigurator

from sam.base.server import Server, SERVER_TYPE_NORMAL

# TODO: refactor, pytest


class ServerTester(object):
    def __init__(self,controlIfName):
        logConfigur = LoggerConfigurator(__name__, './log',
            'databaseAgent.log', level='info')
        self.logger = logConfigur.getLogger()

        server = Server(controlIfName, "192.168.122.222", SERVER_TYPE_NORMAL)

        server.updateIfSet()

        ifset = server.getIfSet()
        self.logger.info(ifset)

        server.printIfSet()

        server.updateControlNICMAC()

        controlNICMac = server.getControlNICMac()
        self.logger.info(controlNICMac)

        server.updateDataPathNICMAC()

        datapathNICMac = server.getDatapathNICMac()
        self.logger.info(datapathNICMac)

        server.printCpuUtil()

if __name__=="__main__":
    controlIfName = "eno1"
    ServerTester(controlIfName)