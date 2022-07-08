#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
Usage:
python3 -m pytest ./test_request.py -s --disable-warnings

Inspect Mysql:
mysql -u dbAgent -p
use Dashboard;
select * from Request;
'''

import uuid
import pytest

from sam.base.request import Request, REQUEST_TYPE_ADD_SFC
from sam.base.messageAgent import REQUEST_PROCESSOR_QUEUE
from sam.dashboard.test.dashboardTestBase import DashboardTestBase
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer


class TestRequestClass(DashboardTestBase):
    @pytest.fixture(scope="function")
    def setup_requestInfo(self):
        # setup
        self.oib = OrchInfoBaseMaintainer("localhost", "dbAgent", "123", reInitialTable=True)
        self.requestNum = 2
        self.addSFCRequestList = self.genAddSFCRequestNameList(self.requestNum)

        yield
        # teardown
        self.delAddSFCRequests(self.addSFCRequestList)

    def genAddSFCRequestNameList(self, requestNum):
        addSFCRequestList = []
        for idx in range(requestNum):
            req = Request(uuid.uuid1(), uuid.uuid1(),
                    REQUEST_TYPE_ADD_SFC, REQUEST_PROCESSOR_QUEUE)
            addSFCRequestList.append(req)
        return addSFCRequestList

    def addAddSFCRequests(self, addSFCRequestList):
        for idx,req in enumerate(addSFCRequestList):
            self.oib.addRequest(req, sfcUUID=uuid.uuid1(),
                                sfciID=idx, cmdUUID=uuid.uuid1())

    def delAddSFCRequests(self, addSFCRequestList):
        for req in addSFCRequestList:
            self.oib.delRequest(req.requestID)

    def test_addRequests(self, setup_requestInfo):
        # exercise
        self.startDjango()
        self.addAddSFCRequests(self.addSFCRequestList)

        # verify
        self.retrieverequestNameList()

    def startDjango(self):
        self.logger.info("You need start django manually!"
            "Then press any key to continue insert data into Mysql Database!")
        input()

    def retrieverequestNameList(self):
        self.logger.info("Please check whether request list are displayed in explorer right.")
        input()
