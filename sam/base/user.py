#!/usr/bin/python
# -*- coding: UTF-8 -*-

class User(object):
    def __init__(self, userID, userType, sfcRequests=None, vnfRequests=None):
        self.userID = userID
        self.userType = userType
        self.sfcRequests = sfcRequests
        self.vnfRequests = vnfRequests