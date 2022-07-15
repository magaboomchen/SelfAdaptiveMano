#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid

from sam.base.command import CMD_STATE_FAIL, CMD_STATE_SUCCESSFUL, CommandReply
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.link import Link
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.messageAgent import DEFAULT_ZONE, SIMULATOR_ZONE, SAMMessage, MessageAgent, \
    MSG_TYPE_SIMULATOR_CMD_REPLY, SIMULATOR_QUEUE
from sam.base.messageAgentAuxillary.msgAgentRPCConf import SIMULATOR_IP, SIMULATOR_PORT
from sam.base.server import SERVER_TYPE_NORMAL, Server
from sam.base.switch import SWITCH_TYPE_NPOP, Switch


class SimulatorStub(object):
    def __init__(self):
        logConfigur = LoggerConfigurator(__name__, './log',
            'measurer.log', level='debug')
        self.logger = logConfigur.getLogger()

        self.mA = MessageAgent()
        self.mA.startMsgReceiverRPCServer(SIMULATOR_IP, SIMULATOR_PORT)

    def sendCmdRply(self,cmdRply):
        msg = SAMMessage(MSG_TYPE_SIMULATOR_CMD_REPLY, cmdRply)
        self.mA.sendMsg(SIMULATOR_QUEUE, msg)
    
    def recvCmdFromMeasurer(self):
        while True:
            msg = self.mA.getMsgByRPC(SIMULATOR_IP, SIMULATOR_PORT)
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
        self.logger.debug(" Simulator gets a command ")
        attributes = {}
        try:
            attributes = self.genTopoAttr()
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, "simulator")
        finally:
            attributes.update({'source':'simulator',
                            'zone':SIMULATOR_ZONE})
            cmdRply = CommandReply(cmd.cmdID, CMD_STATE_SUCCESSFUL, attributes)
            rplyMsg = SAMMessage(MSG_TYPE_SIMULATOR_CMD_REPLY, cmdRply)
        return rplyMsg

    def genTopoAttr(self):
        switchDict = {}
        switch = Switch(uuid.uuid1(), SWITCH_TYPE_NPOP)
        switchDict[switch.switchID] = switch

        linkDict = {}
        link = Link(1,2)
        linkDict[(1,2)] = link

        return {'switches':switchDict,
                'links':linkDict,
                'zone':DEFAULT_ZONE
                }

    def genServerAttr(self):
        serverDict = {}
        server = Server("ens3", "2.2.0.34", SERVER_TYPE_NORMAL)
        server.setServerID(10001)
        serverDict[10001] = server

        return {'servers':serverDict}
