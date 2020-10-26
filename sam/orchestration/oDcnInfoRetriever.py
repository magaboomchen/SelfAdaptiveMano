#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid

from sam.base.messageAgent import *
from sam.measurement.dcnInfoBaseMaintainer import *


class ODCNInfoRetriever(object):
    def __init__(self, dib, logger):
        self._dib = dib
        self.logger = logger
        self._messageAgent = MessageAgent(logger)
        self._messageAgent.startRecvMsg(DCN_INFO_RECIEVER_QUEUE)

    def getDCNInfo(self):
        self._requestDCNInfo()
        self._recvDCNInfo()

    def _requestDCNInfo(self):
        request = Request(0, uuid.uuid1(), REQUEST_TYPE_GET_DCN_INFO,
            DCN_INFO_RECIEVER_QUEUE)
            # ORCHESTRATOR_QUEUE) # it seems that this should be DCN_INFO_RECIEVER_QUEUE, may be delete this comment later
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
                    return 
                else:
                    self.logger.error("Unknown massage body:{0}".format(body))

    def _replyHandler(self, reply):
        self.logger.debug(reply)
        for key, values in reply.attributes.items():
            if key == 'servers':
                self._dib.updateServersInAllZone(values)
            elif key == 'switches':
                self._dib.updateSwitchesInAllZone(values)
            elif key == 'links':
                self._dib.updateLinksInAllZone(values)
            elif key == 'vnfis':
                self._dib.updateVnfisInAllZone(values)
            else:
                self.logger.error("Unknown reply attributes:{0}".format(
                    key
                ))

