#!/usr/bin/python
# -*- coding: UTF-8 -*-

from __future__ import print_function
import logging

from google.protobuf.any_pb2 import Any
import grpc

from sam.base.server import Server
from sam.base.messageAgent import *
from sam.base.sfc import *
from sam.base.socketConverter import SocketConverter
from sam.serverController.sffController.sibMaintainer import *
from sam.serverController.sffController.sffSFCIAdder import *
from sam.serverController.sffController.sffSFCIDeleter import *
from sam.serverController.sffController.sffMonitor import *

# TODO: finish sfci monitor

class SFFControllerCommandAgent(object):
    def __init__(self):
        self._commandsInfo = {}
        logConfigur = LoggerConfigurator(__name__, './log',
            'sffController.log', level='debug')
        self.logger = logConfigur.getLogger()

        self.sibms = SIBMS(self.logger)

        self.sffSFCIAdder = SFFSFCIAdder(self.sibms, self.logger)
        self.sffSFCIDeleter = SFFSFCIDeleter(self.sibms, self.logger)
        self.sffMonitor = SFFMonitor(self.sibms, self.logger)

        self._messageAgent = MessageAgent(self.logger)
        self._messageAgent.startRecvMsg(SFF_CONTROLLER_QUEUE)

    def startSFFControllerCommandAgent(self):
        while True:
            msg = self._messageAgent.getMsg(SFF_CONTROLLER_QUEUE)
            if msg.getMessageType() == MSG_TYPE_SSF_CONTROLLER_CMD:
                self.logger.info("SFF controller get a command.")
                try:
                    cmd = msg.getbody()
                    self._commandsInfo[cmd.cmdID] = {"cmd":cmd,
                        "state":CMD_STATE_PROCESSING}
                    if cmd.cmdType == CMD_TYPE_ADD_SFCI:
                        self.sffSFCIAdder.addSFCIHandler(cmd)
                    elif cmd.cmdType == CMD_TYPE_DEL_SFCI:
                        self.sffSFCIDeleter.delSFCIHandler(cmd)
                    elif cmd.cmdType == CMD_TYPE_GET_SFCI_STATE:
                        self.sffMonitor.monitorSFCIHandler(cmd)
                    else:
                        self.logger.error("Unkonwn sff command type.")
                    self._commandsInfo[cmd.cmdID]["state"] = CMD_STATE_SUCCESSFUL
                except ValueError as err:
                    self.logger.error('sff controller command processing error: ' +
                        repr(err))
                    self._commandsInfo[cmd.cmdID]["state"] = CMD_STATE_FAIL
                except Exception as ex:
                    template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                    message = template.format(type(ex).__name__, ex.args)
                    self.logger.error("SFF Controller occure error: {0}".format(message))
                    self._commandsInfo[cmd.cmdID]["state"] = CMD_STATE_FAIL
                finally:
                    cmdRply = CommandReply(
                        cmd.cmdID,self._commandsInfo[cmd.cmdID]["state"])
                    cmdRply.attributes["source"] = {"sffController"}
                    rplyMsg = SAMMessage(MSG_TYPE_SSF_CONTROLLER_CMD_REPLY,
                        cmdRply)
                    self._messageAgent.sendMsg(MEDIATOR_QUEUE,rplyMsg)
            elif msg.getMessageType() == None:
                pass
            else:
                self.logger.error("Unknown msg type.")

if __name__=="__main__":
    sC = SFFControllerCommandAgent()
    sC.startSFFControllerCommandAgent()