#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
Usage:
python3 -m pytest ./test_user.py -s --disable-warnings
'''

import sys
import time
import uuid
import random
import logging

import pytest

from sam.base.command import *
from sam.base.switch import *
from sam.base.server import *
from sam.base.link import *
from sam.base.user import *
from sam.dashboard.dashboardInfoBaseMaintainer import *

logging.basicConfig(level=logging.INFO)


class TestUserClass(object):
    @pytest.fixture(scope="function")
    def setup_userInfo(self):
        # setup
        self.dashib = DashboardInfoBaseMaintainer("localhost", "dbAgent", "123")
        self.userNum = 2
        userList = self.genUserList(self.userNum)
        self.addUsers(userList)

        yield
        # teardown
        self.delUsers(userList)

    def genUserList(self, userNum):
        userList = []
        for idx in range(userNum):
            cu = CloudUser(uuid.uuid1(), "user{0}".format(idx), "normal")
            userList.append(cu)
        return userList

    def addUsers(self, userList):
        for user in userList:
            self.dashib.addUser(user.userName, user.userID, user.userType)

    def delUsers(self, userList):
        for user in userList:
            self.dashib.delUser(user.userID)

    def test_addUsers(self, setup_userInfo):
        # exercise
        self.startDjango()

        # verify
        self.retrieveUserList()

    def startDjango(self):
        print("You need start django manually!"
            "Then press any key to continue!")
        input()

    def retrieveUserList(self):
        print("Please check whether user list are displayed in explorer right.")
        input()
