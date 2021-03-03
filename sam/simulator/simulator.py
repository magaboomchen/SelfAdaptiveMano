#!/usr/bin/python
# -*- coding: UTF-8 -*-

import time
import uuid

from sam.base.messageAgent import *
from sam.base.sfc import *
from sam.base.switch import *
from sam.base.server import *
from sam.base.link import *
from sam.base.vnf import *
from sam.base.command import *
from sam.base.shellProcessor import ShellProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.simulator.simulatorInfoBaseMaintainer import SimulatorInfoBaseMaintainer


class Simulator(object):
    def __init__(self):
        logConfigur = LoggerConfigurator(__name__, './log',
                            'simulator.log', level='debug')
        self.logger = logConfigur.getLogger()
        self.logger.setLevel(logging.DEBUG)
        self.logger.info("Init simulator.")

        self._cm = CommandMaintainer()

        self._sib = SimulatorInfoBaseMaintainer()

        self._messageAgent = MessageAgent(self.logger)
        # set RabbitMqServer ip, user, passwd into your settings
        # For example, your virtual machine's ip address is 192.168.5.124
        # your rabbitmqServerUserName is "mq"
        # your rabbitmqServerUserCode is "123456"
        self._messageAgent.setRabbitMqServer("192.168.5.124", "mq", "123456")
        self._messageAgent.startRecvMsg(SIMULATOR_QUEUE)

    def startSimulator(self):
        try:
            while True:
                msg = self._messageAgent.getMsg(SIMULATOR_QUEUE)
                msgType = msg.getMessageType()
                if msgType == None:
                    pass
                else:
                    body = msg.getbody()
                    if self._messageAgent.isCommand(body):
                        self._commandHandler(body)
                    else:
                        raise ValueError("Unknown massage body")
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, "simulator")

    def _commandHandler(self,cmd):
        self.logger.debug(" Simulator gets a command ")
        self._cm.addCmd(cmd)
        try:
            if cmd.cmdType == CMD_TYPE_ADD_SFC:
                self._addSFCHandler(cmd)
            elif cmd.cmdType == CMD_TYPE_ADD_SFCI:
                self._addSFCIHandler(cmd)
            elif cmd.cmdType == CMD_TYPE_DEL_SFCI:
                self._delSFCIHandler(cmd)
            elif cmd.cmdType == CMD_TYPE_DEL_SFC:
                self._delSFCHandler(cmd)
            elif cmd.cmdType == CMD_TYPE_GET_SERVER_SET:
                self._getServerSetHandler(cmd)
            elif cmd.cmdType == CMD_TYPE_GET_TOPOLOGY:
                self._getTopologyHandler(cmd)
            # elif cmd.cmdType == CMD_TYPE_GET_SFCI_STATE:
            #     self._getSFCIStateHandler(cmd)
            elif cmd.cmdType == CMD_TYPE_GET_FLOW_SET:
                self._getFlowSetHandler(cmd)
            else:
                raise ValueError("Unkonwn command type.")
            self._cm.changeCmdState(cmd.cmdID, CMD_STATE_SUCCESSFUL)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, "simulator")
            self._cm.changeCmdState(cmd.cmdID, CMD_STATE_FAIL)
        finally:
            cmdRply = CommandReply(cmd.cmdID, self._cm.getCmdState(cmd.cmdID))
            cmdRply.attributes["source"] = {"simulator"}
            rplyMsg = SAMMessage(MSG_TYPE_SIMULATOR_CMD_REPLY, cmdRply)
            self._messageAgent.sendMsg(MEDIATOR_QUEUE, rplyMsg)

    def _addSFCHandler(self, cmd):
        pass
        # TODO

    def _addSFCIHandler(self, cmd):
        pass
        # TODO

    def _delSFCIHandler(self, cmd):
        pass
        # TODO

    def _delSFCHandler(self, cmd):
        pass
        # TODO

    def _getServerSetHandler(self, cmd):
        pass
        # TODO

    def _getTopologyHandler(self, cmd):
        pass
        # TODO

    # def _getSFCIStateHandler(self, cmd):
    #     pass
    #     # TODO

    def _getFlowSetHandler(self, cmd):
        pass
        # TODO


if __name__ == "__main__":
    s = Simulator()
    s.startSimulator()
