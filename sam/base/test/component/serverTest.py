#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging

from sam.base.server import Server, SERVER_TYPE_NORMAL

# TODO: refactor, pytest


class ServerTester(object):
    def __init__(self,controlIfName):
        server = Server(controlIfName, "192.168.122.222", SERVER_TYPE_NORMAL)

        server.updateIfSet()

        ifset = server.getIfSet()
        logging.info(ifset)

        server.printIfSet()

        server.updateControlNICMAC()

        controlNICMac = server.getControlNICMac()
        logging.info(controlNICMac)

        server.updateDataPathNICMAC()

        datapathNICMac = server.getDatapathNICMac()
        logging.info(datapathNICMac)

        server.printCpuUtil()

if __name__=="__main__":
    logging.basicConfig(level=logging.INFO)
    controlIfName = "eno1"
    ServerTester(controlIfName)