#!/usr/bin/python
# -*- coding: UTF-8 -*-

import ctypes
import inspect
import logging

from sam.base.messageAgent import MessageAgent, SAMMessage, \
    MEDIATOR_QUEUE, SIMULATOR_QUEUE, MSG_TYPE_SIMULATOR_CMD_REPLY
from sam.base.command import CommandReply, CommandMaintainer, CMD_TYPE_ADD_SFC, \
    CMD_TYPE_ADD_SFCI, CMD_TYPE_DEL_SFCI, CMD_TYPE_DEL_SFC, CMD_TYPE_GET_SERVER_SET, \
    CMD_TYPE_GET_TOPOLOGY, CMD_TYPE_GET_SFCI_STATE, CMD_STATE_SUCCESSFUL, CMD_STATE_FAIL
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.orchestration.test.fixtures.simulator.cliThread import CLIThread
from sam.orchestration.test.fixtures.simulator.simulatorInfoBaseMaintainer import SimulatorInfoBaseMaintainer


class Simulator(object):
    def __init__(self):
        logConfigur = LoggerConfigurator(__name__, './log',
            'simulator.log', level='debug')
        self.logger = logConfigur.getLogger()
        self.logger.setLevel(logging.DEBUG)
        self.logger.info("Init simulator.")

        self._cm = CommandMaintainer()

        self._sib = SimulatorInfoBaseMaintainer()

        self._threadList = []

        self._messageAgent = MessageAgent(self.logger)
        self._messageAgent.setRabbitMqServer("192.168.0.194", "mq", "123456")
        self._messageAgent.startRecvMsg(SIMULATOR_QUEUE)

    def startCLI(self):
        try:
            # start a command line interface thread
            thread = CLIThread(len(self._threadList), self._sib)
            self._threadList.append(thread)
            thread.setDaemon(True)
            thread.start()
        except:
            self.logger.error("start CLI failed.")

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

    def _commandHandler(self, command):
        self.logger.debug(" Simulator gets a command")
        self._cm.addCmd(command)
        try:
            if command.cmdType == CMD_TYPE_ADD_SFC:
                self._addSFCHandler(command)
            elif command.cmdType == CMD_TYPE_ADD_SFCI:
                self._addSFCIHandler(command)
            elif command.cmdType == CMD_TYPE_DEL_SFCI:
                self._delSFCIHandler(command)
            elif command.cmdType == CMD_TYPE_DEL_SFC:
                self._delSFCHandler(command)
            elif command.cmdType == CMD_TYPE_GET_SERVER_SET:
                self._getServerSetHandler(command)
            elif command.cmdType == CMD_TYPE_GET_TOPOLOGY:
                self._getTopologyHandler(command)
            elif command.cmdType == CMD_TYPE_GET_SFCI_STATE:
                self._getSFCIStateHandler(command)
            else:
                raise ValueError("Unkonwn command type.")
            self._cm.changeCmdState(command.cmdID, CMD_STATE_SUCCESSFUL)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, "simulator")
            self._cm.changeCmdState(command.cmdID, CMD_STATE_FAIL)
        finally:
            cmdRply = CommandReply(command.cmdID, self._cm.getCmdState(
                command.cmdID))
            cmdRply.attributes["source"] = {"simulator"}
            rplyMsg = SAMMessage(MSG_TYPE_SIMULATOR_CMD_REPLY, cmdRply)
            self._messageAgent.sendMsg(MEDIATOR_QUEUE, rplyMsg)

    def _addSFCHandler(self, command):
        pass
        # TODO

    def _addSFCIHandler(self, command):
        pass
        # TODO

    def _delSFCIHandler(self, command):
        pass
        # TODO

    def _delSFCHandler(self, command):
        pass
        # TODO

    def _getServerSetHandler(self, command):
        pass
        # TODO

    def _getTopologyHandler(self, command):
        pass
        # TODO

    def _getSFCIStateHandler(self, command):
        pass
        # TODO

    def __del__(self):
        self.logger.info("Delete Simulator.")
        for thread in self._threadList.itervalues():
            self.logger.debug("check thread is alive?")
            if thread.isAlive():
                self.logger.info("Kill thread: %d" %thread.ident)
                self._async_raise(thread.ident, KeyboardInterrupt)
                thread.join()

    def _async_raise(self,tid, exctype):
        """raises the exception, performs cleanup if needed"""
        tid = ctypes.c_long(tid)
        if not inspect.isclass(exctype):
            exctype = type(exctype)
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid,
            ctypes.py_object(exctype))
        if res == 0:
            raise ValueError("Invalid thread id")
        elif res != 1:
            # """if it returns a number greater than one, you're in trouble,
            # and you should call it again with exc=NULL to revert the effect"""
            ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
            raise SystemError("PyThreadState_SetAsyncExc failed")


if __name__ == "__main__":
    s = Simulator()
    s.startCLI()
    s.startSimulator()
