#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.command import CMD_STATE_SUCCESSFUL, CommandReply
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.messageAgent import TURBONET_ZONE, SAMMessage, MessageAgent, MEDIATOR_QUEUE, \
    MSG_TYPE_SFF_CONTROLLER_CMD_REPLY
from sam.base.messageAgentAuxillary.msgAgentRPCConf import SFF_CONTROLLER_IP, SFF_CONTROLLER_PORT
from sam.base.path import DIRECTION0_PATHID_OFFSET, MAPPING_TYPE_MMLPSFC, ForwardingPathSet
from sam.base.sfc import SFCI
from sam.base.slo import SLO
from sam.base.vnfiStatus import VNFIStatus
from sam.base.vnf import VNF_TYPE_RATELIMITER, VNFI


class SFFControllerStub(object):
    def __init__(self):
        logConfigur = LoggerConfigurator(__name__, './log',
            'sffController.log', level='debug')
        self.logger = logConfigur.getLogger()

        self.mA = MessageAgent()
        self.mA.startMsgReceiverRPCServer(SFF_CONTROLLER_IP, SFF_CONTROLLER_PORT)

    def sendCmdRply(self,cmdRply):
        msg = SAMMessage(MSG_TYPE_SFF_CONTROLLER_CMD_REPLY, cmdRply)
        self.mA.sendMsg(MEDIATOR_QUEUE, msg)

    def recvCmdFromMeasurer(self):
        while True:
            msg = self.mA.getMsgByRPC(SFF_CONTROLLER_IP, SFF_CONTROLLER_PORT)
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
        self.logger.debug(" SFFController gets a command ")
        attributes = {}
        try:
            attributes = self.genSFCIAttr()
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, "sffController")
        finally:
            attributes.update({'source':'sffController', 'zone':TURBONET_ZONE})
            cmdRply = CommandReply(cmd.cmdID, CMD_STATE_SUCCESSFUL, attributes)
            rplyMsg = SAMMessage(MSG_TYPE_SFF_CONTROLLER_CMD_REPLY, cmdRply)
        return rplyMsg

    def genSFCIAttr(self):
        sfciDict = {}
        vnfiSeq = [
                    [VNFI(VNF_TYPE_RATELIMITER,VNF_TYPE_RATELIMITER,1,1,1,
                            VNFIStatus(
                                inputTrafficAmount=100,
                                inputPacketAmount=100,
                                outputTrafficAmount=50,
                                outputPacketAmount=50
                            ))
                    ]
                ]

        slo = SLO()
        fPS = ForwardingPathSet(
            {DIRECTION0_PATHID_OFFSET:[
                [(0,10001), (0,1), (0,2), (0,10003)],
                [(0,10003), (0,2), (0,1), (0,10001)]
            ]},
            MAPPING_TYPE_MMLPSFC,
            {DIRECTION0_PATHID_OFFSET:[
                []
            ]}
        )
        sfci = SFCI(1,vnfiSequence=vnfiSeq,sloRealTimeValue=slo, forwardingPathSet=fPS)
        sfciDict[1] = sfci

        return {'sfcisDict':sfciDict,
                'zone':TURBONET_ZONE
                }
