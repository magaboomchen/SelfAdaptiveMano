#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
Usage:
python3 -m pytest ./test_server.py -s --disable-warnings

Inspect Mysql:
mysql -u dbAgent -p
use Measurer;
select * from Server;
'''

import sys
import time
if sys.version < '3':
    try:
        input = raw_input
    except NameError:
        pass
import uuid

import pytest

from sam.base.server import *
from sam.base.messageAgent import *
from sam.dashboard.test.dashboardTestBase import DashboardTestBase
from sam.measurement.dcnInfoBaseMaintainer import DCNInfoBaseMaintainer


class TestServerClass(DashboardTestBase):
    @pytest.fixture(scope="function")
    def setup_serverInfo(self):
        # setup
        self.dcnIB = DCNInfoBaseMaintainer()
        self.dcnIB.enableDataBase("localhost", "dbAgent", "123")
        self.serverNum = 10
        self.serverList = self.genServerList(self.serverNum)

        yield
        # teardown
        self.delServers(self.serverList)

    def genServerList(self, serverNum):
        serverList = []
        for idx in range(serverNum):
            se = Server("wifi0", "192.168.123.123", SERVER_TYPE_NORMAL)
            se.setServerID(uuid.uuid1())
            serverIPInt = self._sc.ip2int("192.168.0.1") + idx
            serverIP = self._sc.int2ip(serverIPInt)
            se.setControlNICIP(serverIP)
            se.updateResource()
            serverList.append(se)
        return serverList

    def addServers(self, serverList):
        for server in serverList:
            self.dcnIB.addServer(server, SIMULATOR_ZONE)

    def delServers(self, serverList):
        for server in serverList:
            self.dcnIB.delServer(server.getServerID(), SIMULATOR_ZONE)

    def test_addServers(self, setup_serverInfo):
        # exercise
        self.startDjango()

        t = time.time()
        print('1time,t')
        self.addServers(self.serverList)

        t2 = time.time()
        print('2time',t2)
        print('total is',t2-t)

        # verify
        self.retrieveServerList()

    def startDjango(self):
        self.logger.info("You need start django manually!"
            "Then press any key to continue insert data into Mysql Database!")
        input()

    def retrieveServerList(self):
        self.logger.info("Please check whether server list are displayed in explorer right.")
        input()
