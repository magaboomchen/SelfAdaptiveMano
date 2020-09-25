#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid
import logging

from sam.base.messageAgent import *
from sam.measurement.dcnInfoBaseMaintainer import *


class ODCNInfoRetriever(object):
    def __init__(self, dib, messageAgent):
        self._dib = dib
        self._messageAgent = messageAgent
        self._messageAgent.startRecvMsg(DCN_INFO_RECIEVER_QUEUE)

    def _getDCNInfo(self):
        self._requestDCNInfo()
        self._recvDCNInfo()

    def _requestDCNInfo(self):
        request = Request(0, uuid.uuid1(), REQUEST_TYPE_GET_DCN_INFO,
            ORCHESTRATOR_QUEUE)
        msg = SAMMessage(MSG_TYPE_REQUEST, request)
        self._messageAgent.sendMsg(MEASURER_QUEUE, msg)

    def _recvDCNInfo(self):
        while True:
            msg = self._messageAgent.getMsg(DCN_INFO_RECIEVER_QUEUE)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            else:
                body = msg.getbody()
                if self._messageAgent.isReply(body):
                    self._replyHandler(body)
                else:
                    logging.error("Unknown massage body:{0}".format(body))

    def _replyHandler(self, reply):
        for key, values in reply.items():
            if key == 'servers':
                self._dib.updateServersInAllZone(values)
            elif key == 'switches':
                self._dib.updateSwitchesInAllZone(values)
            elif key == 'links':
                self._dib.updateLinksInAllZone(values)
            elif key == 'vnfis':
                self._dib.updateVnfisInAllZone(values)
            else:
                logging.error("Unknown reply attributes:{0}".format(
                    key
                ))
