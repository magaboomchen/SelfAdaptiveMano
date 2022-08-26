#!/usr/bin/python
# -*- coding: UTF-8 -*-

import time
from typing import Dict
from logging import Logger

from sam.base.sfc import SFC, SFCI
from sam.base.messageAgent import DISPATCHER_QUEUE, MSG_TYPE_REQUEST, MessageAgent, SAMMessage
from sam.base.request import REQUEST_TYPE_DEL_SFC, REQUEST_TYPE_DEL_SFCI, REQUEST_TYPE_UPDATE_SFC_STATE, Request
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.sfcConstant import STATE_ACTIVE, STATE_MANUAL
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer


class RequestHandler(object):
    def __init__(self, logger, msgAgent, oib):
        # type: (Logger, MessageAgent, OrchInfoBaseMaintainer) -> None
        self.logger = logger
        self._messageAgent = msgAgent
        self._oib = oib
        self._taskDict = {
            REQUEST_TYPE_UPDATE_SFC_STATE: {},
            REQUEST_TYPE_DEL_SFCI: {},
            REQUEST_TYPE_DEL_SFC: {}
        }    # type: Dict[Request.requestType, Dict[Request.requestID, Request]]

    def handle(self, request):
        # type: (Request) -> None
        try:
            self.logger.info("Get a request")
            if request.requestType == REQUEST_TYPE_UPDATE_SFC_STATE:
                sfc = request.attributes["sfc"] # type: SFC
                sfcState = self._oib.getSFCState(sfc.sfcUUID)
                newState = request.attributes["newState"]
                if newState == STATE_MANUAL and sfcState == STATE_ACTIVE:
                    self._oib.updateSFCState(sfc.sfcUUID, newState)
                    if request.requestID in self._taskDict[REQUEST_TYPE_UPDATE_SFC_STATE]:
                        del self._taskDict[REQUEST_TYPE_UPDATE_SFC_STATE]
                elif newState == STATE_ACTIVE and sfcState == STATE_MANUAL:
                    self._oib.updateSFCState(sfc.sfcUUID, newState)
                    if request.requestID in self._taskDict[REQUEST_TYPE_UPDATE_SFC_STATE]:
                        del self._taskDict[REQUEST_TYPE_UPDATE_SFC_STATE]
                else:
                    self._taskDict[REQUEST_TYPE_UPDATE_SFC_STATE][request.requestID] = request
            elif request.requestType == REQUEST_TYPE_DEL_SFCI:
                sfc = request.attributes["sfc"]     # type: SFC
                sfci = request.attributes["sfci"]   # type: SFCI
                sfcState = self._oib.getSFCState(sfc.sfcUUID)
                if self._isValidDelSFCIRequest(sfcState, sfci.sfciID):
                    self.sendRequest2Dispatcher(request)
                    if request.requestID in self._taskDict[REQUEST_TYPE_DEL_SFCI]:
                        del self._taskDict[REQUEST_TYPE_DEL_SFCI]
                else:
                    self._taskDict[REQUEST_TYPE_DEL_SFCI][request.requestID] = request
            elif request.requestType == REQUEST_TYPE_DEL_SFC:
                sfc = request.attributes["sfc"]
                if self._oib._isDelSFCValidState(sfc.sfcUUID):
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

    def _isValidDelSFCIRequest(self, sfcState, sfciID):
        return sfcState == STATE_MANUAL and self._oib._isDelSFCIValidState(sfciID)

    def sendRequest2Dispatcher(self, request):
        msg = SAMMessage(MSG_TYPE_REQUEST, request)
        self._messageAgent.sendMsg(DISPATCHER_QUEUE, msg)

    def processAllRequestTask(self):
        self.logger.debug("process all requests.")
        for requestType, requestDict in list(self._taskDict.items()):
            for requestID, request in list(requestDict.items()):
                self.handle(request)