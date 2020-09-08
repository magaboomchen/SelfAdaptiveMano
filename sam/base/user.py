#!/usr/bin/python
# -*- coding: UTF-8 -*-

class User(object):
    def __init__(self, userID, userType, SFCRequests=None, VNFRequests=None):
        self.userID = userID
        self.userType = userType
        self.SFCRequests = SFCRequests
        self.VNFRequests = VNFRequests