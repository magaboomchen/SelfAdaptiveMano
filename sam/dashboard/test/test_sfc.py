#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
Usage:
python3 -m pytest ./test_sfc.py -s --disable-warnings

Inspect Mysql:
mysql -u dbAgent -p
use Dashboard;
select * from SFC;
'''

import sys
if sys.version < '3':
    try:
        input = raw_input
    except NameError:
        pass
import uuid
import pytest

from sam.base.sfc import *
from sam.base.messageAgent import *
from sam.dashboard.test.dashboardTestBase import DashboardTestBase
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer


class TestSFCClass(DashboardTestBase):
    @pytest.fixture(scope="function")
    def setup_sfcInfo(self):
        # setup
        self.oib = OrchInfoBaseMaintainer("localhost", "dbAgent", "123")
        self.sfcNum = 2
        self.SFCList = self.genSFCList(self.sfcNum)

        yield
        # teardown
        self.delSFCs(self.SFCList)

    def genSFCList(self, sfcNum):
        addSFCSFCList = []
        for idx in range(sfcNum):
            sfc = SFC(uuid.uuid1(), [VNF_TYPE_FW], 1, 0, "NORTHSOUTH_WEBSITE")
            sfc.attributes["zone"] = SIMULATOR_ZONE
            addSFCSFCList.append(sfc)
        return addSFCSFCList

    def addSFCs(self, addSFCSFCList):
        for idx,sfc in enumerate(addSFCSFCList):
            self.oib.addSFC(sfc, sfciIDList=[idx])

    def delSFCs(self, addSFCSFCList):
        for sfc in addSFCSFCList:
            self.oib.delSFC(sfc.sfcUUID)

    def test_addSFCs(self, setup_sfcInfo):
        # exercise
        self.startDjango()
        self.addSFCs(self.SFCList)

        # verify
        self.retrievesfcNameList()

    def startDjango(self):
        self.logger.info("You need start django manually!"
            "Then press any key to continue insert data into Mysql Database!")
        input()

    def retrievesfcNameList(self):
        self.logger.info("Please check whether sfc list are displayed in explorer right.")
        input()
