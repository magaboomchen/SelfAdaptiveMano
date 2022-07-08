#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
Usage:
python3 -m pytest ./test_switch.py -s --disable-warnings

Inspect Mysql:
mysql -u dbAgent -p
use Measurer;
select * from Switch;
'''

import pytest

from sam.base.switch import Switch, SWITCH_TYPE_FORWARD
from sam.base.messageAgent import SIMULATOR_ZONE
from sam.dashboard.test.dashboardTestBase import DashboardTestBase
from sam.measurement.dcnInfoBaseMaintainer import DCNInfoBaseMaintainer


class TestSwitchClass(DashboardTestBase):
    @pytest.fixture(scope="function")
    def setup_switchInfo(self):
        # setup
        self.dcnIB = DCNInfoBaseMaintainer()
        self.dcnIB.enableDataBase("localhost", "dbAgent", "123")
        self.switchNum = 2
        self.switchList = self.genSwitchList(self.switchNum)

        yield
        # teardown
        self.delSwitchs(self.switchList)

    def genSwitchList(self, switchNum):
        switchList = []
        for idx in range(switchNum):
            sw = Switch(idx, SWITCH_TYPE_FORWARD)
            switchList.append(sw)
        return switchList

    def addSwitchs(self, switchList):
        for switch in switchList:
            self.dcnIB.addSwitch(switch, SIMULATOR_ZONE)

    def delSwitchs(self, switchList):
        for switch in switchList:
            self.dcnIB.delSwitch(switch.switchID, SIMULATOR_ZONE)

    def test_addSwitchs(self, setup_switchInfo):
        # exercise
        self.startDjango()
        self.addSwitchs(self.switchList)

        # verify
        self.retrieveSwitchList()

    def startDjango(self):
        self.logger.info("You need start django manually!"
            "Then press any key to continue insert data into Mysql Database!")
        input()

    def retrieveSwitchList(self):
        self.logger.info("Please check whether switch list are displayed in explorer right.")
        input()
