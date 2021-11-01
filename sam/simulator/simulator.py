#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging
import os
import random
import threading
import time
from Queue import Queue
from getopt import getopt

from sam.base.command import CommandMaintainer, CMD_STATE_FAIL, \
    CMD_STATE_SUCCESSFUL, CommandReply
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.flow import Flow
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.messageAgent import MessageAgent, SIMULATOR_QUEUE, SAMMessage, MSG_TYPE_SIMULATOR_CMD_REPLY, \
    MEDIATOR_QUEUE
from sam.base.path import *
from sam.simulator.commend_handler import commend_handler
from sam.simulator.op_handler import op_handler
from sam.simulator.simulatorInfoBaseMaintainer import SimulatorInfoBaseMaintainer


# import subprocess
# predictor=subprocess.Popen(('python3','predict.py'),cwd=os.path.dirname(os.path.abspath(__file__)), stdin=subprocess.PIPE, stdout=subprocess.PIPE)

# def predict(target, competitors):
#     assert isinstance(target, NF)
#     for competitor in competitors:
#         assert isinstance(competitor, NF)
#     predictor.stdin.write('%d'%len(competitors))
#     predictor.stdin.write(str(target))
#     for competitor in competitors:
#         predictor.stdin.write(str(competitor))
#     return float(predictor.stdout.readline())

# predictor = subprocess.Popen(('python3', 'predict.py'), cwd=os.path.dirname(os.path.abspath(__file__)),
#                              stdin=subprocess.PIPE, stdout=subprocess.PIPE)


# def predict(target, competitors):
# assert isinstance(target, NF)
# for competitor in competitors:
#     assert isinstance(competitor, NF)
# predictor.stdin.write('%d' % len(competitors))
# predictor.stdin.write(str(target))
# for competitor in competitors:
#     predictor.stdin.write(str(competitor))
# return float(predictor.stdout.readline())


class Simulator(object):
    def __init__(self, op_input):
        # type: (Queue) -> None
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

        self.op_input = op_input

    def get_op_input(self):
        self.op_input.join()
        try:
            while True:
                time.sleep(0.2)
                self.op_input.put(raw_input('> '))
                self.op_input.join()
        except EOFError:
            pass

    def startSimulator(self):
        try:
            thrd = threading.Thread(target=self.get_op_input, name='simulator input')
            thrd.setDaemon(True)
            thrd.start()
            while True:
                if not self.op_input.empty():
                    command = self.op_input.get()
                    command = command.strip()
                    if command:
                        self._op_input_handler(command)
                    self.op_input.task_done()

                msg = self._messageAgent.getMsg(SIMULATOR_QUEUE)
                msgType = msg.getMessageType()
                if msgType == None:
                    pass
                else:
                    body = msg.getbody()
                    if self._messageAgent.isCommand(body):
                        self._command_handler(body)
                    else:
                        raise ValueError("Unknown massage body")
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, "simulator")

    def _command_handler(self, cmd):
        self.logger.debug(" Simulator gets a command ")
        self._cm.addCmd(cmd)
        attributes = {}
        try:
            attributes = commend_handler(cmd, self._sib)
            self._cm.changeCmdState(cmd.cmdID, CMD_STATE_SUCCESSFUL)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, "simulator")
            self._cm.changeCmdState(cmd.cmdID, CMD_STATE_FAIL)
        finally:
            cmdRply = CommandReply(cmd.cmdID, self._cm.getCmdState(cmd.cmdID), dict(attributes, source='simulator'))
            rplyMsg = SAMMessage(MSG_TYPE_SIMULATOR_CMD_REPLY, cmdRply)
            self._messageAgent.sendMsg(MEDIATOR_QUEUE, rplyMsg)

    def _op_input_handler(self, cmd_str):
        self.logger.debug('Simulator received operator input: ' + cmd_str)
        try:
            cmd_type = cmd_str.split(' ', 1)[0].lower()
            op_handler(cmd_type, cmd_str, self._sib)
            print('OK: ' + cmd_str)
        except Exception as ex:
            print('FAIL: ' + cmd_str)
            ExceptionProcessor(self.logger).logException(ex, "simulator command")


if __name__ == "__main__":
    op_input = Queue()
    op_input.put('reset')
    self_location = os.path.dirname(os.path.abspath(__file__))
    try:
        init_file = open(os.path.join(self_location, 'simulator_init_TEST'), 'r')
    except IOError:
        try:
            init_file = open(os.path.join(self_location, 'simulator_init'), 'r')
        except IOError:
            pass
    try:
        for line in init_file:
            op_input.put(line)
    except NameError:
        pass
    s = Simulator(op_input)
    try:
        s.startSimulator()
    except KeyboardInterrupt as e:
        # predictor.terminate()
        raise e
