#!/usr/bin/python
# -*- coding: UTF-8 -*-

from __future__ import print_function
import grpc
import logging

import sam.serverController.builtin_pb.service_pb2 as service_pb2
import sam.serverController.builtin_pb.service_pb2_grpc as service_pb2_grpc
import sam.serverController.builtin_pb.bess_msg_pb2 as bess_msg_pb2
import sam.serverController.builtin_pb.module_msg_pb2 as module_msg_pb2
import sam.serverController.builtin_pb.ports.port_msg_pb2 as port_msg_pb2

from sam.base.server import Server
from sam.base.messageAgent import *
from sam.base.sfc import *
from sam.base.command import *
from sam.base.path import *
from sam.serverController.classifierController.cibMaintainer import *
from sam.serverController.classifierController.classifierSFCIAdder import *
from sam.serverController.classifierController.classifierSFCIDeleter import *

class ClassifierControllerCommandAgent(object):
    def __init__(self):
        logConfigur = LoggerConfigurator(__name__, './log',
            'classifierController.log', level='info')
        self.logger = logConfigur.getLogger()
        self.logger.info("Initialize classifier controller command agent.")
        self._commandsInfo = {}

        self.cibms = CIBMS()

        self.clsfSFCIAdder = ClassifierSFCIAdder(self.cibms, self.logger)
        self.clsfSFCIDeleter = ClassifierSFCIDeleter(self.cibms, self.logger)

        self._messageAgent = MessageAgent(self.logger)
        self._messageAgent.startRecvMsg(SERVER_CLASSIFIER_CONTROLLER_QUEUE)

    def startClassifierControllerCommandAgent(self):
        while True:
            msg = self._messageAgent.getMsg(SERVER_CLASSIFIER_CONTROLLER_QUEUE)
            if msg.getMessageType() == MSG_TYPE_CLASSIFIER_CONTROLLER_CMD:
                self.logger.info("Classifier controller get a command.")
                try:
                    cmd = msg.getbody()
                    self._commandsInfo[cmd.cmdID] = {"cmd":cmd,
                        "state":CMD_STATE_PROCESSING}
                    if cmd.cmdType == CMD_TYPE_ADD_SFCI:
                        self.clsfSFCIAdder.addSFCIHandler(cmd)
                    elif cmd.cmdType == CMD_TYPE_DEL_SFCI:
                        self.clsfSFCIDeleter.delSFCIHandler(cmd)
                    else:
                        self.logger.error("Unkonwn classifier command type.")
                    self._commandsInfo[cmd.cmdID]["state"] = CMD_STATE_SUCCESSFUL
                except ValueError as err:
                    self.logger.error('classifier command processing error: ' +
                        repr(err))
                    self._commandsInfo[cmd.cmdID]["state"] = CMD_STATE_FAIL
                except Exception as ex:
                    template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                    message = template.format(type(ex).__name__, ex.args)
                    self.logger.error("Classifier Controller occure error: {0}".format(message))
                    self._commandsInfo[cmd.cmdID]["state"] = CMD_STATE_FAIL
                finally:
                    rplyMsg = SAMMessage(MSG_TYPE_CLASSIFIER_CONTROLLER_CMD_REPLY, 
                        CommandReply(cmd.cmdID,self._commandsInfo[cmd.cmdID]["state"]))
                    self._messageAgent.sendMsg(MEDIATOR_QUEUE,rplyMsg)
            elif msg.getMessageType() == None:
                pass
            else:
                self.logger.error("Unknown msg type.")

if __name__=="__main__":
    cC = ClassifierControllerCommandAgent()
    cC.startClassifierControllerCommandAgent()