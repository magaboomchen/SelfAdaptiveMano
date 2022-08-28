#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
Usage:
python3 -m pytest ./test_link.py -s --disable-warnings

Inspect Mysql:
mysql -u dbAgent -p
use Measurer;
select * from Link;
'''

import pytest

from sam.base.link import Link
from sam.base.messageAgent import SIMULATOR_ZONE
from sam.dashboard.backup.test.dashboardTestBase import DashboardTestBase
from sam.measurement.dcnInfoBaseMaintainer import DCNInfoBaseMaintainer


class TestLinkClass(DashboardTestBase):
    @pytest.fixture(scope="function")
    def setup_linkInfo(self):
        # setup
        self.dcnIB = DCNInfoBaseMaintainer()
        self.dcnIB.enableDataBase("localhost", "dbAgent", "123")
        self.linkNum = 2
        self.linkList = self.genLinkList(self.linkNum)

        yield
        # teardown
        self.delLinks(self.linkList)

    def genLinkList(self, linkNum):
        linkList = []
        for idx in range(linkNum):
            li = Link(idx, idx+1)
            linkList.append(li)
        return linkList

    def addLinks(self, linkList):
        for link in linkList:
            self.dcnIB.addLink(link, SIMULATOR_ZONE)

    def delLinks(self, linkList):
        for link in linkList:
            self.dcnIB.delLink(link, SIMULATOR_ZONE)

    def test_addLinks(self, setup_linkInfo):
        # exercise
        self.startDjango()
        self.addLinks(self.linkList)

        # verify
        self.retrieveLinkList()

    def startDjango(self):
        self.logger.info("You need start django manually!"
            "Then press any key to continue insert data into Mysql Database!")
        input()

    def retrieveLinkList(self):
        self.logger.info("Please check whether link list are displayed in explorer right.")
        input()
