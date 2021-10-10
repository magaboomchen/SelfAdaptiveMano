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

import uuid

import pytest

from sam.base.server import *
from sam.dashboard.dashboardInfoBaseMaintainer import DashboardInfoBaseMaintainer
from sam.dashboard.test.dashboardTestBase import DashboardTestBase


class TestServerClass(DashboardTestBase):
    @pytest.fixture(scope="function")
    def setup_serverInfo(self):
        raise ValueError("Unimplementation!需要重构")
        # setup
        self.dashib = DashboardInfoBaseMaintainer("localhost", "dbAgent", "123")
        self.serverNum = 2
        serverList = self.genServerList(self.serverNum)
        self.addServers(serverList)

        yield
        # teardown
        self.delServers(serverList)

    # def genServerList(self, serverNum):
    #     serverList = []
    #     for idx in range(serverNum):
    #         cu = Server(uuid.uuid1(), "server{0}".format(idx), "normal")
    #         serverList.append(cu)
    #     return serverList

    # def addServers(self, serverList):
    #     for server in serverList:
    #         self.dashib.addServer(server.serverName, server.serverID, server.serverType)

    # def delServers(self, serverList):
    #     for server in serverList:
    #         self.dashib.delServer(server.serverID)

    # def test_addServers(self, setup_serverInfo):
    #     # exercise
    #     self.startDjango()

    #     # verify
    #     self.retrieveServerList()

    # def startDjango(self):
    #     self.logger.info("You need start django manually!"
    #         "Then press any key to continue insert data into Mysql Database!")
    #     input()

    # def retrieveServerList(self):
    #     self.logger.info("Please check whether server list are displayed in explorer right.")
    #     input()
