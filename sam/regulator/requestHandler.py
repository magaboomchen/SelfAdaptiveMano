#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.messageAgent import DISPATCHER_QUEUE, MSG_TYPE_REQUEST, SAMMessage
from sam.base.request import REQUEST_TYPE_DEL_SFC, REQUEST_TYPE_DEL_SFCI, REQUEST_TYPE_UPDATE_SFC_STATE
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.sfc import STATE_ACTIVE, STATE_MANUAL


class RequestHandler(object):
    def __init__(self, logger, msgAgent, oib):
        self.logger = logger
        self._messageAgent = msgAgent
        self._oib = oib
        self._taskDict = {
            REQUEST_TYPE_UPDATE_SFC_STATE: {},
            REQUEST_TYPE_DEL_SFCI: {},
            REQUEST_TYPE_DEL_SFC: {}
        }    # dict[requestType, dict[Request.requestID, Request]]

    def handle(self, request):
        try:
            self.logger.info("Get a request")
            if request.requestType == REQUEST_TYPE_UPDATE_SFC_STATE:
                sfc = request.attributes["sfc"]
                sfcState = self._oib.getSFCState(sfc.sfcUUID)
                if sfcState == STATE_ACTIVE:
                    self._oib.updateSFCState(sfc.sfcUUID, STATE_MANUAL)
                    if request.requestID in self._taskDict[REQUEST_TYPE_UPDATE_SFC_STATE]:
                        del self._taskDict[REQUEST_TYPE_UPDATE_SFC_STATE]
                else:
                    self._taskDict[REQUEST_TYPE_UPDATE_SFC_STATE][request.requestID] = request
            elif request.requestType == REQUEST_TYPE_DEL_SFCI:
                sfc = request.attributes["sfc"]
                sfcState = self._oib.getSFCState(sfc.sfcUUID)
                if sfcState == STATE_MANUAL:
                    self.sendRequest2Dispatcher(request)
                    if request.requestID in self._taskDict[REQUEST_TYPE_DEL_SFCI]:
                        del self._taskDict[REQUEST_TYPE_DEL_SFCI]
                else:
                    self._taskDict[REQUEST_TYPE_DEL_SFCI][request.requestID] = request
            elif request.requestType == REQUEST_TYPE_DEL_SFC:
                sfc = request.attributes["sfc"]
                sfcState = self._oib.getSFCState(sfc.sfcUUID)
                if sfcState == STATE_MANUAL:
                    self.sendRequest2Dispatcher(request)
                    if request.requestID in self._taskDict[REQUEST_TYPE_DEL_SFC]:
                        del self._taskDict[REQUEST_TYPE_DEL_SFC]
                else:
                    self._taskDict[REQUEST_TYPE_DEL_SFC][request.requestID] = request
            else:
                pass
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, 
                "Regualtor request handler")
        finally:
            pass

    def sendRequest2Dispatcher(self, request):
        msg = SAMMessage(MSG_TYPE_REQUEST, request)
        self._messageAgent.sendMsg(DISPATCHER_QUEUE, msg)

    def processAllRequestTask(self):
        for requestType, requestDict in list(self._taskDict.items()):
            for requestID, request in list(requestDict.items()):
                self.handle(request)