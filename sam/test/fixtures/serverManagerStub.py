#!/usr/bin/python
# -*- coding: UTF-8 -*-

import datetime
from sam.base.command import CMD_STATE_SUCCESSFUL, CommandReply
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.messageAgent import TURBONET_ZONE, SAMMessage, MessageAgent, \
    MSG_TYPE_SERVER_MANAGER_CMD_REPLY, MEDIATOR_QUEUE
from sam.base.messageAgentAuxillary.msgAgentRPCConf import SERVER_MANAGER_IP, SERVER_MANAGER_PORT
from sam.base.server import SERVER_TYPE_NORMAL, Server


class ServerManagerStub(object):
    def __init__(self):
        logConfigur = LoggerConfigurator(__name__, './log',
            'serverManager.log', level='debug')
        self.logger = logConfigur.getLogger()

        self.mA = MessageAgent()
        self.mA.startMsgReceiverRPCServer(SERVER_MANAGER_IP, SERVER_MANAGER_PORT)

    def sendCmdRply(self,cmdRply):
        msg = SAMMessage(MSG_TYPE_SERVER_MANAGER_CMD_REPLY, cmdRply)
        self.mA.sendMsg(MEDIATOR_QUEUE, msg)

    def recvCmdFromMeasurer(self):
        while True:
            msg = self.mA.getMsgByRPC(SERVER_MANAGER_IP, SERVER_MANAGER_PORT)
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
        self.logger.debug(" Server Manager gets a command ")
        attributes = {}
        try:
            attributes = self.genServerAttr()
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, "serverManager")
        finally:
            attributes.update({'source':'serverManger',
                                'zone':TURBONET_ZONE})
            cmdRply = CommandReply(cmd.cmdID, CMD_STATE_SUCCESSFUL,
                                    attributes=attributes)
            rplyMsg = SAMMessage(MSG_TYPE_SERVER_MANAGER_CMD_REPLY, cmdRply)
        return rplyMsg

    def genServerAttr(self):
        serverInfoDict = {}
        server = Server("ens3", "2.2.0.34", SERVER_TYPE_NORMAL)
        server.setServerID(10001)
        serverInfoDict = {10001:
                    {
                        'server':server, 'Active':True, 
                        'timestamp':datetime.datetime.now(),
                        'Status':None}
                }

        return {'servers':serverInfoDict,
                'zone':TURBONET_ZONE
            }
