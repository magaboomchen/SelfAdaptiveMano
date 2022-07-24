#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.request import REQUEST_TYPE_DEL_SFC
from sam.base.exceptionProcessor import ExceptionProcessor


class RequestHandler(object):
    def __init__(self, logger, msgAgent, oib):
        self.logger = logger
        self._messageAgent = msgAgent
        self._oib = oib

    def handle(self, request):
        try:
            self.logger.info("Get a request")
            if request.requestType == REQUEST_TYPE_DEL_SFC:
                pass
            else:
                pass
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, 
                "Regualtor request handler")
        finally:
            pass
