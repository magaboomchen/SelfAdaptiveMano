#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid
from sam.base.link import Link
from sam.base.request import REQUEST_STATE_SUCCESSFUL, Reply, Request
from sam.base.sfc import SFCI
from sam.base.slo import SLO
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.messageAgent import MSG_TYPE_REQUEST, TURBONET_ZONE, SAMMessage, MessageAgent
from sam.base.messageAgentAuxillary.msgAgentRPCConf import DEFINABLE_MEASURER_IP, DEFINABLE_MEASURER_PORT


class TurbonetStub(object):
    def __init__(self):
        logConfigur = LoggerConfigurator(__name__, './log',
            'serverManager.log', level='debug')
        self.logger = logConfigur.getLogger()

        self.mA = MessageAgent()
        self.mA.startMsgReceiverRPCServer(DEFINABLE_MEASURER_IP, DEFINABLE_MEASURER_PORT)

    def recvCmdFromMeasurer(self):
        while True:
            msg = self.mA.getMsgByRPC(DEFINABLE_MEASURER_IP, DEFINABLE_MEASURER_PORT)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            else:
                body = msg.getbody()
                source = msg.getSource()
                try:
                    if self.mA.isRequest(body):
                        rplyMsg = self._request_handler(body)
                        self.mA.sendMsgByRPC(source["srcIP"], source["srcPort"], rplyMsg)
                        break
                    elif self.mA.isCommand(body):
                        pass
                    else:
                        self.logger.error("Unknown massage body")
                except Exception as ex:
                    ExceptionProcessor(self.logger).logException(ex,
                        "measurer")

    def _request_handler(self, request):
        self.logger.debug(" Turbonet gets a request ")
        attributes = {}
        try:
            attributes = self.genLinksAttr()
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, "turbonet")
        finally:
            attributes.update({'source':'turbonet', 'zone':TURBONET_ZONE})
            cmdRply = Reply(uuid.uuid1(), REQUEST_STATE_SUCCESSFUL, attributes)
            rplyMsg = SAMMessage(MSG_TYPE_REQUEST, cmdRply)
        return rplyMsg

    def genLinksAttr(self):
        linkDict = {}
        linkDict[(1,2)] = {
            "link": Link(1,2,queueLatency=10)
        }
        linkDict[(2,1)] = {
            "link": Link(2,1,queueLatency=15)
        }

        return {'links':{TURBONET_ZONE:linkDict},
                'zone':TURBONET_ZONE
                }

