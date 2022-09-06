#!/usr/bin/python
# -*- coding: UTF-8 -*-

from typing import Any, Dict, Union
from uuid import UUID

REQUEST_STATE_INITIAL = "REQUEST_STATE_INITIAL"
REQUEST_STATE_IN_PROCESSING = "REQUEST_STATE_IN_PROCESSING"
REQUEST_STATE_SUCCESSFUL = "REQUEST_STATE_SUCCESSFUL"
REQUEST_STATE_FAILED = "REQUEST_STATE_FAILED"
REQUEST_STATE_REJECT = "REQUEST_STATE_REJECT"

REQUEST_TYPE_GET_LINK_INFO = "REQUEST_TYPE_GET_LINK_INFO"
REQUEST_TYPE_GET_DCN_INFO = "REQUEST_TYPE_GET_DCN_INFO"
REQUEST_TYPE_GET_SFCI_STATE = "REQUEST_TYPE_GET_SFCI_STATE"
REQUEST_TYPE_ADD_SFC = "REQUEST_TYPE_ADD_SFC"
REQUEST_TYPE_ADD_SFCI = "REQUEST_TYPE_ADD_SFCI"
REQUEST_TYPE_DEL_SFCI = "REQUEST_TYPE_DEL_SFCI"
REQUEST_TYPE_DEL_SFC = "REQUEST_TYPE_DEL_SFC"
REQUEST_TYPE_UPDATE_SFC_STATE = "REQUEST_TYPE_UPDATE_SFC_STATE"


class Request(object):
    def __init__(self, userID,      # type: int
                requestID,          # type: UUID
                requestType,        # type: Union[REQUEST_TYPE_GET_LINK_INFO, REQUEST_TYPE_GET_DCN_INFO]
                requestSrcQueue=None,   # type: str
                requestSource=None, # type: Dict[str, Any]
                requestState=REQUEST_STATE_INITIAL, # type: Union[REQUEST_STATE_INITIAL, REQUEST_STATE_SUCCESSFUL]
                attributes=None     # type: Dict[str, Any]
            ):
        self.userID =  userID # 0 is root
        self.requestID = requestID
        self.requestType = requestType
        self.requestSrcQueue = requestSrcQueue
        self.requestSource = requestSource
        # e.g. {"srcIP": "10.0.0.1", "srcPort": 50001}
        self.requestState = requestState
        self.attributes = attributes
        # e.g. {'sfc':sfc, 'error':error}

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)


class Reply(object):
    def __init__(self, requestID,   # type: UUID
                requestState,       # type: Union[REQUEST_STATE_INITIAL, REQUEST_STATE_SUCCESSFUL]
                attributes=None     # type: Dict[str, Any]
            ):
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
