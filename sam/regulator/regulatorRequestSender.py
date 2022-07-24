#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid
import time
import threading

from sam.base.messageAgent import MSG_TYPE_REQUEST, SAMMessage
from sam.base.messageAgentAuxillary.msgAgentRPCConf import MEASURER_IP, MEASURER_PORT
from sam.base.request import Request, REQUEST_TYPE_GET_SFCI_STATE
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.regulator.config import TRAFFIC_LOAD_DETECT_TIMESLOT


class RegulatorRequestSender(threading.Thread):
    def __init__(self, threadID, messageAgent, logger):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self._messageAgent = messageAgent
        self.logger = logger

    def run(self):
        self.logger.debug("thread RegulatorRequestSender.run().")
        while True:
            try:
                self.sendGetSFCIStatusRequest()
            except Exception as ex:
                ExceptionProcessor(self.logger).logException(ex)
            finally:
                time.sleep(TRAFFIC_LOAD_DETECT_TIMESLOT)

    def sendGetSFCIStatusRequest(self):
        getSFCIStateRequest = Request(uuid.uuid1(), uuid.uuid1(), 
                                        REQUEST_TYPE_GET_SFCI_STATE)
        msg = SAMMessage(MSG_TYPE_REQUEST, getSFCIStateRequest)
        self._messageAgent.sendMsgByRPC(MEASURER_IP, MEASURER_PORT, msg)
