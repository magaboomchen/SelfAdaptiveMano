#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid

from sam.base.sfc import SFC, SFCI
from sam.base.request import REQUEST_TYPE_ADD_SFC, REQUEST_TYPE_ADD_SFCI, \
                        REQUEST_TYPE_DEL_SFC, REQUEST_TYPE_DEL_SFCI, Request


class RequestGenerator(object):
    def __init__(self):
        pass

    def genAddSFCRequest(self, sfc, zoneName):
        # type: (SFC, str) -> Request
        req = Request(0, uuid.uuid1(), REQUEST_TYPE_ADD_SFC, 
                        attributes={
                            "sfc": sfc,
                            "zone": zoneName
                    })
        return req

    def genAddSFCIRequest(self, sfc, sfci, zoneName):
        # type: (SFC, SFCI, str) -> Request
        req = Request(0, uuid.uuid1(), REQUEST_TYPE_ADD_SFCI, 
                        attributes={
                            "sfc": sfc,
                            "sfci": sfci,
                            "zone": zoneName
                    })
        return req

    def genDelSFCIRequest(self, sfc, sfci, zoneName):
        # type: (SFC, SFCI, str) -> Request
        req = Request(0, uuid.uuid1(), REQUEST_TYPE_DEL_SFCI, 
                        attributes={
                            "sfc": sfc,
                            "sfci": sfci,
                            "zone": zoneName
                    })
        return req

    def genDelSFCRequest(self, sfc, zoneName):
        # type: (SFC, str) -> Request
        req = Request(0, uuid.uuid1(), REQUEST_TYPE_DEL_SFC, 
                        attributes={
                            "sfc": sfc,
                            "zone": zoneName
                    })
        return req
