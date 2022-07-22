#!/usr/bin/python
# -*- coding: UTF-8 -*-

REQUEST_STATE_INITIAL = "REQUEST_STATE_INITIAL"
REQUEST_STATE_IN_PROCESSING = "REQUEST_STATE_IN_PROCESSING"
REQUEST_STATE_SUCCESSFUL = "REQUEST_STATE_SUCCESSFUL"
REQUEST_STATE_FAILED = "REQUEST_STATE_FAILED"

REQUEST_TYPE_GET_DCN_INFO = "REQUEST_TYPE_GET_DCN_INFO"
REQUEST_TYPE_GET_SFCI_STATE = "REQUEST_TYPE_GET_SFCI_STATE"
REQUEST_TYPE_ADD_SFC = "REQUEST_TYPE_ADD_SFC"
REQUEST_TYPE_ADD_SFCI = "REQUEST_TYPE_ADD_SFCI"
REQUEST_TYPE_DEL_SFCI = "REQUEST_TYPE_DEL_SFCI"
REQUEST_TYPE_DEL_SFC = "REQUEST_TYPE_DEL_SFC"


class Request(object):
    def __init__(self, userID, requestID, requestType, requestSrcQueue=None,
            requestSource=None, requestState=REQUEST_STATE_INITIAL,
            attributes=None):
        self.userID =  userID # 0 is root
        self.requestID = requestID # uuid1()
        self.requestType = requestType
        self.requestSrcQueue = requestSrcQueue
        self.requestSource = requestSource
        self.requestState = requestState
        self.attributes = attributes
        # {'sfc':sfc, 'error':error}

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)


class Reply(object):
    def __init__(self, requestID, requestState, attributes=None):
        self.requestID = requestID
        self.requestState = requestState
        self.attributes = attributes

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)
