#!/usr/bin/python
# -*- coding: UTF-8 -*-

from __future__ import print_function

from sam.base.messageAgent import MEASURER_QUEUE, SAMMessage, MessageAgent, SFF_CONTROLLER_QUEUE, \
    MSG_TYPE_SFF_CONTROLLER_CMD, MEDIATOR_QUEUE, MSG_TYPE_SFF_CONTROLLER_CMD_REPLY
from sam.base.command import CommandReply, CMD_STATE_PROCESSING, CMD_TYPE_PAUSE_BESS, \
    CMD_TYPE_RESUME_BESS, CMD_TYPE_ADD_SFCI, CMD_TYPE_DEL_SFCI, CMD_TYPE_GET_SFCI_STATE, \
    CMD_STATE_SUCCESSFUL, CMD_STATE_FAIL
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.loggerConfigurator import LoggerConfigurator

from sam.serverController.sffController.sfcConfig import DEFAULT_CHAIN_TYPE
from sam.serverController.sffController.sffSFCIAdder import SFFSFCIAdder
from sam.serverController.sffController.sffSFCIDeleter import SFFSFCIDeleter
from sam.serverController.sffController.sffMonitor import SFFMonitor
from sam.serverController.sffController.sffFailureEmulator import SFFFailureEmulator
from sam.serverController.sffController.sibMaintainer import SIBMS
from sam.serverController.sffController.argParser import ArgParser

# TODO: finish sfci monitor


class SFFControllerCommandAgent(object):
    def __init__(self, zoneName=""):
        self._commandsInfo = {}
        logConfigur = LoggerConfigurator(__name__, './log',
            'sffController.log', level='debug')
        self.logger = logConfigur.getLogger()

        self.zoneName = zoneName

        self.sibms = SIBMS(self.logger)

        self.sffSFCIAdder = SFFSFCIAdder(self.sibms, self.logger)
        self.sffSFCIDeleter = SFFSFCIDeleter(self.sibms, self.logger)
        self.sffMonitor = SFFMonitor(self.sibms, self.logger)
        self.sffFailureEmulator = SFFFailureEmulator(self.sibms, self.logger)

        self._messageAgent = MessageAgent(self.logger)
        self.queueName = self._messageAgent.genQueueName(SFF_CONTROLLER_QUEUE, zoneName)
        self.logger.info("Listen on {0}".format(self.queueName))
        self._messageAgent.startRecvMsg(self.queueName)

    def startSFFControllerCommandAgent(self):
        while True:
            msg = self._messageAgent.getMsg(self.queueName)
            if msg.getMessageType() == MSG_TYPE_SFF_CONTROLLER_CMD:
                self.logger.info("SFF controller get a command.")
                cmd = msg.getbody()
                self._commandsInfo[cmd.cmdID] = {"cmd":cmd,
                    "state":CMD_STATE_PROCESSING}

                self.logger.info("cmdID: {0}".format(cmd.cmdID))

                # special commands
                if cmd.cmdType in [ CMD_TYPE_PAUSE_BESS, CMD_TYPE_RESUME_BESS]:
                    try:
                        if cmd.cmdType == CMD_TYPE_PAUSE_BESS:
                            self.sffFailureEmulator.emulateSoftwareFailure(cmd)
                        elif cmd.cmdType == CMD_TYPE_RESUME_BESS:
                            self.logger.info("recovery!")
                            self.sffFailureEmulator.emulateSoftwareFailureRecovery(cmd)
                        else:
                            self.logger.error("Unkonwn sff command type.")
                            raise ValueError("Unkonwn sff command type.")
                    except ValueError as err:
                        self.logger.error('sff controller command processing error: ' +
                            repr(err))
                    continue

                # common commands
                try:
                    resDict = {}
                    if cmd.cmdType == CMD_TYPE_ADD_SFCI:
                        self.sffSFCIAdder.addSFCIHandler(cmd)
                    elif cmd.cmdType == CMD_TYPE_DEL_SFCI:
                        self.sffSFCIDeleter.delSFCIHandler(cmd)
                    elif cmd.cmdType == CMD_TYPE_GET_SFCI_STATE:
                        resDict = self.sffMonitor.monitorSFCIHandler()
                    else:
                        self.logger.error("Unkonwn sff command type.")
                        raise ValueError("Unkonwn sff command type.")
                    self._commandsInfo[cmd.cmdID]["state"] = CMD_STATE_SUCCESSFUL
                except ValueError as err:
                    self.logger.error('sff controller command processing error: ' +
                        repr(err))
                    self._commandsInfo[cmd.cmdID]["state"] = CMD_STATE_FAIL
                except Exception as ex:
                    ExceptionProcessor(self.logger).logException(ex, "SFF Controller")
                    self._commandsInfo[cmd.cmdID]["state"] = CMD_STATE_FAIL
                finally:
                    cmdRply = CommandReply(
                        cmd.cmdID,self._commandsInfo[cmd.cmdID]["state"])
                    cmdRply.attributes["source"] = {"sffController"}
                    cmdRply.attributes["zone"] = self.zoneName
                    cmdRply.attributes.update(resDict)
                    rplyMsg = SAMMessage(MSG_TYPE_SFF_CONTROLLER_CMD_REPLY,
                                                                    cmdRply)
                    queueName = MEDIATOR_QUEUE
                    if cmd.cmdType == CMD_TYPE_GET_SFCI_STATE:
                        queueName = MEASURER_QUEUE
                    self._messageAgent.sendMsg(queueName, rplyMsg)
            elif msg.getMessageType() == None:
                pass
            else:
                self.logger.error("Unknown msg type.")

if __name__=="__main__":
    argParser = ArgParser()
    zoneName = argParser.getArgs()['zoneName']   # example: None parameter
    sC = SFFControllerCommandAgent(zoneName)
    sC.startSFFControllerCommandAgent()