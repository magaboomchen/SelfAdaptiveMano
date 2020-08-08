#!/usr/bin/env python
from __future__ import print_function
import grpc
import os
from google.protobuf.any_pb2 import Any
import pika
import base64
import pickle
import time
import uuid
import subprocess
import logging
import Queue
import struct

import sam.serverController.builtin_pb.service_pb2 as service_pb2
import sam.serverController.builtin_pb.service_pb2_grpc as service_pb2_grpc
import sam.serverController.builtin_pb.bess_msg_pb2 as bess_msg_pb2
import sam.serverController.builtin_pb.module_msg_pb2 as module_msg_pb2
import sam.serverController.builtin_pb.ports.port_msg_pb2 as port_msg_pb2

from sam.base.server import Server
from sam.base.messageAgent import *
from sam.base.sfc import *
from sam.base.socketConverter import SocketConverter as SC
from sam.base.command import *
from sam.base.path import *
from sam.serverController.classifierController.classifierIBMaintainer import *
from sam.serverController.classifierController.sFCinitializer import *
from sam.serverController.classifierController.sFCAdder import *
from sam.serverController.classifierController.sFCDeleter import *
from sam.serverController.classifierController.sFCIAdder import *
from sam.serverController.classifierController.sFCIDeleter import *

# Classifier Controller's Responsibilities
# 1: recv/send commands from orchetration
# 2: 5 command processors
# 3: classifier set maintainer

class ClassifierControllerCommandAgent(object):
    def __init__(self):
        logging.info("Initialize classifier controller command agent.")
        self._commandsInfo = {}
        self._messageAgent = MessageAgent()
        self._messageAgent.startRecvMsg(SERVER_CLASSIFIER_CONTROLLER_QUEUE)

    def startClassifierControllerCommandAgent(self,sfcInitializer,sfcAdder,
        sfcDeleter,sfciAdder,sfciDeleter):
        while True:
            msg = self._messageAgent.getMsg(SERVER_CLASSIFIER_CONTROLLER_QUEUE)
            if msg.getMessageType() == MSG_TYPE_CLASSIFIER_CONTROLLER_CMD:
                logging.info("Classifier controller get a command.")
                try:
                    cmd = msg.getbody()
                    self._commandsInfo[cmd.cmdID] = {"cmd":cmd,
                        "state":CMD_STATE_PROCESSING}
                    if cmd.cmdType == CMD_TYPE_INIT_CLASSIFIER: TODO# TODO： 删除这一项
                        sfcInitializer.initClassifier(cmd)
                    elif cmd.cmdType == CMD_TYPE_ADD_CLASSIFIER_SFC: # TODO： 删除这一项
                        sfcAdder.addSFC(cmd)
                    elif cmd.cmdType == CMD_TYPE_DEL_CLASSIFIER_SFC: # TODO： 删除这一项
                        sfcDeleter.delSFC(cmd)
                    elif cmd.cmdType == CMD_TYPE_ADD_SFCI:
                        sfciAdder.addSFCI(cmd)
                    elif cmd.cmdType == CMD_TYPE_DEL_SFCI:
                        sfciDeleter.delSFCI(cmd)
                    else:
                        logging.error("Unkonwn classifier command type.")
                    self._commandsInfo[cmd.cmdID]["state"] = CMD_STATE_SUCCESSFUL
                except ValueError as err:
                    logging.error('classifier command processing error: ' +
                        repr(err))
                    self._commandsInfo[cmd.cmdID]["state"] = CMD_STATE_FAIL
                finally:
                    rplyMsg = SAMMessage(MSG_TYPE_CLASSIFIER_CONTROLLER_CMD_REPLY, 
                        CommandReply(cmd.cmdID,self._commandsInfo[cmd.cmdID]["state"]))
                    self._messageAgent.sendMsg(ORCHESTRATION_QUEUE,rplyMsg)
            elif msg.getMessageType() == None:
                pass
            else:
                logging.error("Unknown msg type.")

if __name__=="__main__":
    logging.basicConfig(level=logging.INFO)

    clsMaintainer = ClassifierIBMaintainer()
    sfcInitializer = ClassifierInitializer(clsMaintainer)
    sfcAdder = SFCAdder(clsMaintainer)
    sfcDeleter = SFCDeleter(clsMaintainer)
    sfciAdder = SFCIAdder(clsMaintainer)
    sfciDeleter = SFCIDeleter(clsMaintainer)

    cC = ClassifierControllerCommandAgent()
    cC.startClassifierControllerCommandAgent(sfcInitializer,sfcAdder,
        sfcDeleter,sfciAdder,sfciDeleter)