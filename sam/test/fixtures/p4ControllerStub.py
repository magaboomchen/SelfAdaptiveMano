#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.sfc import SFCI
from sam.base.slo import SLO
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.vnfiStatus import VNFIStatus
from sam.base.vnf import VNF_TYPE_RATELIMITER, VNFI
from sam.base.command import CMD_STATE_SUCCESSFUL, CommandReply
from sam.base.messageAgent import MSG_TYPE_P4CONTROLLER_CMD_REPLY, \
                                    TURBONET_ZONE, SAMMessage, MessageAgent
from sam.base.messageAgentAuxillary.msgAgentRPCConf import P4_CONTROLLER_IP, P4_CONTROLLER_PORT


class P4ControllerStub(object):
    def __init__(self):
        logConfigur = LoggerConfigurator(__name__, './log',
            'serverManager.log', level='debug')
        self.logger = logConfigur.getLogger()

        self.mA = MessageAgent()
        self.mA.startMsgReceiverRPCServer(P4_CONTROLLER_IP, P4_CONTROLLER_PORT)

    def recvCmdFromMeasurer(self):
        while True:
            msg = self.mA.getMsgByRPC(P4_CONTROLLER_IP, P4_CONTROLLER_PORT)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            else:
                body = msg.getbody()
                source = msg.getSource()
                try:
                    if self.mA.isRequest(body):
                        pass
                    elif self.mA.isCommand(body):
                        rplyMsg = self._command_handler(body)
                        self.mA.sendMsgByRPC(source["srcIP"], source["srcPort"], rplyMsg)
                        break
                    else:
                        self.logger.error("Unknown massage body")
                except Exception as ex:
                    ExceptionProcessor(self.logger).logException(ex,
                        "measurer")

    def _command_handler(self, cmd):
        self.logger.debug(" P4Controller gets a command ")
        attributes = {}
        try:
            attributes = self.genSFCIAttr()
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, "p4Controller")
        finally:
            attributes.update({'source':'p4Controller', 'zone':TURBONET_ZONE})
            cmdRply = CommandReply(cmd.cmdID, CMD_STATE_SUCCESSFUL, attributes)
            rplyMsg = SAMMessage(MSG_TYPE_P4CONTROLLER_CMD_REPLY, cmdRply)
        return rplyMsg

    def genSFCIAttr(self):
        sfciDict = {}
        vnfiSeq = [[VNFI(VNF_TYPE_RATELIMITER,VNF_TYPE_RATELIMITER,1,1,1,VNFIStatus())]]
        slo = SLO()
        sfci = SFCI(1,vnfiSequence=vnfiSeq,sloRealTimeValue=slo)
        sfciDict[1] = sfci

        return {'sfcisDict':sfciDict,
                'zone':TURBONET_ZONE
                }

