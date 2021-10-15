#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
Usage:
python3 -m pytest ./test_zone.py -s --disable-warnings

Inspect Mysql:
mysql -u dbAgent -p
use Dashboard;
select * from Zone;
'''

import sys
if sys.version < '3':
    try:
        input = raw_input
    except NameError:
        pass
import pytest

from sam.dashboard.dashboardInfoBaseMaintainer import *
from sam.dashboard.test.dashboardTestBase import DashboardTestBase


class TestZoneClass(DashboardTestBase):
    @pytest.fixture(scope="function")
    def setup_zoneInfo(self):
        # setup
        self.dashib = DashboardInfoBaseMaintainer("localhost", "dbAgent", "123")
        self.zoneNum = 2
        self.zoneNameList = self.genZoneNameList(self.zoneNum)

        yield
        # teardown
        self.delZones(self.zoneNameList)

    def genZoneNameList(self, zoneNum):
        zoneNameList = []
        for idx in range(zoneNum):
            cu = "zone{0}".format(idx)
            zoneNameList.append(cu)
        return zoneNameList

    def addZones(self, zoneNameList):
        for zoneName in zoneNameList:
            self.dashib.addZone(zoneName)

    def delZones(self, zoneNameList):
        for zoneName in zoneNameList:
            self.dashib.delZone(zoneName)

    def test_addZones(self, setup_zoneInfo):
        # exercise
        self.startDjango()
        self.addZones(self.zoneNameList)

        # verify
        self.retrievezoneNameList()

    def startDjango(self):
        self.logger.info("You need start django manually!"
            "Then press any key to continue insert data into Mysql Database!")
        input()

    def retrievezoneNameList(self):
        self.logger.info("Please check whether zone list are displayed in explorer right.")
        input()
