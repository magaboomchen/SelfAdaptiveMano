#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid
import time

from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.regulator.config import TRAFFIC_LOAD_DETECT_TIMESLOT
from sam.base.request import Request, REQUEST_TYPE_GET_SFCI_STATE
from sam.base.messageAgent import MSG_TYPE_REQUEST, MessageAgent, SAMMessage
from sam.base.messageAgentAuxillary.msgAgentRPCConf import MEASURER_IP, MEASURER_PORT, REGULATOR_IP, REGULATOR_PORT


class RegulatorRequestSender(object):
    def __init__(self):
        self.logConfigur = LoggerConfigurator(__name__, './log',
            'regulatorRequestSender.log',
            level='debug')
        self.logger = self.logConfigur.getLogger()
        self._messageAgent = MessageAgent(self.logger)
        self._messageAgent.setListenSocket(REGULATOR_IP, REGULATOR_PORT)

    def run(self):
        self.logger.debug("process RegulatorRequestSender.run().")
        lastTime = time.time()
        while True:
            currentTime = time.time()
            if currentTime - lastTime > TRAFFIC_LOAD_DETECT_TIMESLOT:
                lastTime = currentTime
                try:
                    self.sendGetSFCIStatusRequest()
                except Exception as ex:
                    ExceptionProcessor(self.logger).logException(ex)
                finally:
                    pass

    def sendGetSFCIStatusRequest(self):
        self.logger.debug("Send get SFCI state request.")
        getSFCIStateRequest = Request(uuid.uuid1(), uuid.uuid1(), 
                                        REQUEST_TYPE_GET_SFCI_STATE)
        msg = SAMMessage(MSG_TYPE_REQUEST, getSFCIStateRequest)
        self._messageAgent.sendMsgByRPC(MEASURER_IP, MEASURER_PORT, msg)


if __name__ == "__main__":
    rRS = RegulatorRequestSender()
    rRS.run()
