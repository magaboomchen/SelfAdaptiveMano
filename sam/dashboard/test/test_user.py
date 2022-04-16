#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
Usage:
python3 -m pytest ./test_user.py -s --disable-warnings

Inspect Mysql:
mysql -u dbAgent -p
use Dashboard;
select * from User;
'''

import sys
if sys.version < '3':
    try:
        input = raw_input
    except NameError:
        pass
import uuid

import pytest

from sam.base.user import CloudUser
from sam.dashboard.dashboardInfoBaseMaintainer import DashboardInfoBaseMaintainer
from sam.dashboard.test.dashboardTestBase import DashboardTestBase


class TestUserClass(DashboardTestBase):
    @pytest.fixture(scope="function")
    def setup_userInfo(self):
        # setup
        self.dashib = DashboardInfoBaseMaintainer("localhost", "dbAgent", "123")
        self.userNum = 2
        self.userList = self.genUserList(self.userNum)

        yield
        # teardown
        self.delUsers(self.userList)

    def genUserList(self, userNum):
        userList = []
        for idx in range(userNum):
            cu = CloudUser(uuid.uuid1(), "user{0}".format(idx), "normal")
            userList.append(cu)
        return userList

    def addUsers(self, userList):
        for user in userList:
            self.dashib.addUser(user)

    def delUsers(self, userList):
        for user in userList:
            self.dashib.delUser(user.userID)

    def test_addUsers(self, setup_userInfo):
        # exercise
        self.startDjango()
        self.addUsers(self.userList)

        # verify
        self.retrieveUserList()

    def startDjango(self):
        self.logger.info("You need start django manually!"
            "Then press any key to continue insert data into Mysql Database!")
        input()

    def retrieveUserList(self):
        self.logger.info("Please check whether user list are displayed in explorer right.")
        input()
