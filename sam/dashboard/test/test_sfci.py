#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
Usage:
python3 -m pytest ./test_sfci.py -s --disable-warnings

Inspect Mysql:
mysql -u dbAgent -p
use Dashboard;
select * from SFCI;
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
from sam.base.vnf import *
from sam.base.messageAgent import *
from sam.dashboard.test.dashboardTestBase import DashboardTestBase
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer


class TestSFCIClass(DashboardTestBase):
    @pytest.fixture(scope="function")
    def setup_sfciInfo(self):
        # setup
        self.oib = OrchInfoBaseMaintainer("localhost", "dbAgent", "123", reInitialTable=True)
        self.sfciNum = 2
        self.SFCIList = self.genSFCIList(self.sfciNum)

        yield
        # teardown
        self.delSFCIs(self.SFCIList)

    def genSFCIList(self, sfciNum):
        addSFCISFCIList = []
        for idx in range(sfciNum):
            sfci = SFCI(idx, [VNF_TYPE_FW, VNF_TYPE_FW, VNFI(uuid.uuid1())])
            addSFCISFCIList.append(sfci)
        return addSFCISFCIList

    def addSFCIs(self, addSFCISFCIList):
        for idx,sfci in enumerate(addSFCISFCIList):
            self.oib.addSFCI(sfci)

    def delSFCIs(self, addSFCISFCIList):
        for sfci in addSFCISFCIList:
            self.oib.delSFCI(sfci.sfciID)

    def test_addSFCIs(self, setup_sfciInfo):
        # exercise
        self.startDjango()
        self.addSFCIs(self.SFCIList)

        # verify
        self.retrievesfciNameList()

    def startDjango(self):
        self.logger.info("You need start django manually!"
            "Then press any key to continue insert data into Mysql Database!")
        input()

    def retrievesfciNameList(self):
        self.logger.info("Please check whether sfci list are displayed in explorer right.")
        input()
