#!/usr/bin/python
# -*- coding: UTF-8 -*-

class CloudUser(object):
    def __init__(self, userID, userName, userType, sfcRequests=None, vnfRequests=None):
        self.userID = userID
        self.userName = userName
        self.userType = userType
        self.sfcRequests = sfcRequests
        self.vnfRequests = vnfRequests