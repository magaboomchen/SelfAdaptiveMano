#!/usr/bin/python
# -*- coding: UTF-8 -*-

from __future__ import print_function
import grpc

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
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.serverController.classifierController.cibMaintainer import *
from sam.serverController.classifierController.classifierSFCIAdder import *
from sam.serverController.classifierController.classifierSFCIDeleter import *
from sam.serverController.classifierController.argParser import ArgParser


class ClassifierControllerCommandAgent(object):
    def __init__(self, zoneName=""):
        logConfigur = LoggerConfigurator(__name__, './log',
            'classifierController.log', level='debug')
        self.logger = logConfigur.getLogger()
        self.logger.info("Initialize classifier controller command agent.")
        self.logger.setLevel(logging.DEBUG)
        self._commandsInfo = {}

        self.cibms = CIBMS()

        self.clsfSFCAdder = ClassifierSFCAdder(self.cibms, self.logger)
        self.clsfSFCIAdder = ClassifierSFCIAdder(self.cibms, self.logger)
        self.clsfSFCIDeleter = ClassifierSFCIDeleter(self.cibms, self.logger)
        self.clsfSFCDeleter = ClassifierSFCDeleter(self.cibms, self.logger)

        self._messageAgent = MessageAgent(self.logger)
        self.queueName = self._messageAgent.genQueueName(
            SERVER_CLASSIFIER_CONTROLLER_QUEUE, zoneName)
        self._messageAgent.startRecvMsg(self.queueName)
        self.logger.info("listen on queueName: {0}".format(self.queueName))

    def startClassifierControllerCommandAgent(self):
        while True:
            msg = self._messageAgent.getMsg(self.queueName)
            if msg.getMessageType() == MSG_TYPE_CLASSIFIER_CONTROLLER_CMD:
                self.logger.info("Classifier controller get a command.")
                try:
                    cmd = msg.getbody()
                    self._commandsInfo[cmd.cmdID] = {"cmd":cmd,
                        "state":CMD_STATE_PROCESSING}
                    if cmd.cmdType == CMD_TYPE_ADD_SFC:
                        self.clsfSFCAdder.addSFCHandler(cmd)
                    elif cmd.cmdType == CMD_TYPE_ADD_SFCI:
                        self.clsfSFCIAdder.addSFCIHandler(cmd)
                    elif cmd.cmdType == CMD_TYPE_DEL_SFCI:
                        self.clsfSFCIDeleter.delSFCIHandler(cmd)
                    elif cmd.cmdType == CMD_TYPE_DEL_SFC:
                        self.clsfSFCDeleter.delSFCHandler(cmd)
                    else:
                        self.logger.error("Unkonwn classifier command type.")
                        raise ValueError("Unkonwn classifier command type.")
                    self._commandsInfo[cmd.cmdID]["state"] = CMD_STATE_SUCCESSFUL
                except ValueError as err:
                    self.logger.error('classifier command processing error:' \
                        + repr(err))
                    self._commandsInfo[cmd.cmdID]["state"] = CMD_STATE_FAIL
                except Exception as ex:
                    ExceptionProcessor(self.logger).logException(ex,
                        " Classifier Controller ")
                    self._commandsInfo[cmd.cmdID]["state"] = CMD_STATE_FAIL
                finally:
                    cmdRply = CommandReply(cmd.cmdID, self._commandsInfo[cmd.cmdID]["state"])
                    cmdRply.attributes["source"] = {"classifierController"}
                    rplyMsg = SAMMessage(MSG_TYPE_CLASSIFIER_CONTROLLER_CMD_REPLY, 
                        cmdRply)
                    self._messageAgent.sendMsg(MEDIATOR_QUEUE,rplyMsg)
            elif msg.getMessageType() == None:
                pass
            else:
                self.logger.error("Unknown msg type.")

if __name__=="__main__":
    argParser = ArgParser()
    zoneName = argParser.getArgs()['zoneName']   # example: None parameter
    cC = ClassifierControllerCommandAgent(zoneName)
    cC.startClassifierControllerCommandAgent()