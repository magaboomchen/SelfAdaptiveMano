#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
Usage:
python3 -m pytest ./test_routingMorphic.py -s --disable-warnings

Inspect Mysql:
mysql -u dbAgent -p
use Dashboard;
select * from RoutingMorphic;
'''

import sys
if sys.version < '3':
    try:
        input = raw_input
    except NameError:
        pass
import pytest

from sam.base.routingMorphic import RoutingMorphic
from sam.dashboard.dashboardInfoBaseMaintainer import DashboardInfoBaseMaintainer
from sam.dashboard.test.dashboardTestBase import DashboardTestBase


class TestRoutingMorphicClass(DashboardTestBase):
    @pytest.fixture(scope="function")
    def setup_routingMorphicInfo(self):
        # setup
        self.dashib = DashboardInfoBaseMaintainer("localhost", "dbAgent", "123")
        self.routingMorphicNum = 2
        self.routingMorphicList = self.genRoutingMorphicList(self.routingMorphicNum)

        yield
        # teardown
        self.delRoutingMorphics(self.routingMorphicList)

    def genRoutingMorphicList(self, routingMorphicNum):
        routingMorphicList = []
        for idx in range(routingMorphicNum):
            rM = RoutingMorphic()
            rM.addMorphicName("routingMorphic{0}".format(idx))
            rM.addIdentifierName("IPv4")
            rM.addHeaderOffsets(14+8)
            rM.addHeaderBits(32)
            rM.addEtherType(0x0800) 
            routingMorphicList.append(rM)
        return routingMorphicList

    def addRoutingMorphics(self, routingMorphicList):
        for routingMorphic in routingMorphicList:
            self.dashib.addRoutingMorphic(routingMorphic)

    def delRoutingMorphics(self, routingMorphicList):
        for routingMorphic in routingMorphicList:
            self.dashib.delRoutingMorphic(routingMorphic)

    def test_addRoutingMorphics(self, setup_routingMorphicInfo):
        # exercise
        self.startDjango()
        self.addRoutingMorphics(self.routingMorphicList)

        # verify
        self.retrieveRoutingMorphicList()

    def startDjango(self):
        self.logger.info("You need start django manually!"
            "Then press any key to continue insert data into Mysql Database!")
        input()

    def retrieveRoutingMorphicList(self):
        self.logger.info("Please check whether routingMorphic list are displayed in explorer right.")
        input()
