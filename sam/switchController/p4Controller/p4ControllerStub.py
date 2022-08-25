#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.command import CommandReply, CMD_STATE_SUCCESSFUL, CMD_STATE_FAIL, CMD_STATE_PROCESSING
from sam.base.messageAgent import SAMMessage, MessageAgent, P4CONTROLLER_QUEUE, MSG_TYPE_P4CONTROLLER_CMD, \
                                    MSG_TYPE_P4CONTROLLER_CMD_REPLY, MEDIATOR_QUEUE, TURBONET_ZONE
from sam.base.messageAgentAuxillary.msgAgentRPCConf import P4_CONTROLLER_PORT, P4_CONTROLLER_IP
from sam.base.loggerConfigurator import LoggerConfigurator

P4CONTROLLER_P4_SWITCH_ID_1 = 20
P4CONTROLLER_P4_SWITCH_ID_2 = 21
DIRECTION_MASK_0 = 8388607
DIRECTION_MASK_1 = 8388608

class P4Controller(object):
    def __init__(self, _zonename):
        logConf = LoggerConfigurator(__name__, './log', 'p4Controller.log', level='debug')
        self.logger = logConf.getLogger()
        self.logger.info('Initialize P4 controller.')
        self.zonename = _zonename
        self._messageAgent = MessageAgent()
        self.queueName = self._messageAgent.genQueueName(P4CONTROLLER_QUEUE, _zonename)
        self._messageAgent.startRecvMsg(self.queueName)
        self._messageAgent.startMsgReceiverRPCServer(P4_CONTROLLER_IP, P4_CONTROLLER_PORT)
        self._commands = {}
        self._commandresults = {}
        self._sfclist = {}
        self.logger.info('P4 controller initialization complete.')

    def run(self):
        while True:
            msg = self._messageAgent.getMsg(self.queueName)
            msgType = msg.getMessageType()
            if msgType == None:
                msg = self._messageAgent.getMsgByRPC(P4_CONTROLLER_IP, P4_CONTROLLER_PORT)
                msgType = msg.getMessageType()
                if msgType == None:
                    pass
                elif msgType == MSG_TYPE_P4CONTROLLER_CMD:
                    self.logger.info('Got a command from rpc')
                    cmd = msg.getbody()
                    source = msg.getSource()
                    self._commands[cmd.cmdID] = cmd
                    self._commandresults[cmd.cmdID] = CMD_STATE_PROCESSING
                    resdict = {}
                    success = True
                    if success:
                        self._commandresults[cmd.cmdID] = CMD_STATE_SUCCESSFUL
                    else:
                        self._commandresults[cmd.cmdID] = CMD_STATE_FAIL
                    cmdreply = CommandReply(cmd.cmdID, self._commandresults[cmd.cmdID])
                    cmdreply.attributes["zone"] = TURBONET_ZONE
                    cmdreply.attributes.update(resdict)
                    replymessage = SAMMessage(MSG_TYPE_P4CONTROLLER_CMD_REPLY, cmdreply)
                    # self._messageAgent.sendMsgByRPC(P4_CONTROLLER_IP, P4_CONTROLLER_PORT, replymessage)
                    self._messageAgent.sendMsgByRPC(source['srcIP'], source['srcPort'], replymessage)
            elif msgType == MSG_TYPE_P4CONTROLLER_CMD:
                self.logger.info('Got a command from rabbitMQ.')
                cmd = msg.getbody()
                self._commands[cmd.cmdID] = cmd
                self._commandresults[cmd.cmdID] = CMD_STATE_PROCESSING
                resdict = {}
                success = True
                if success:
                    self._commandresults[cmd.cmdID] = CMD_STATE_SUCCESSFUL
                else:
                    self._commandresults[cmd.cmdID] = CMD_STATE_FAIL
                cmdreply = CommandReply(cmd.cmdID, self._commandresults[cmd.cmdID])
                cmdreply.attributes["zone"] = TURBONET_ZONE
                cmdreply.attributes.update(resdict)
                replymessage = SAMMessage(MSG_TYPE_P4CONTROLLER_CMD_REPLY, cmdreply)
                self._messageAgent.sendMsg(MEDIATOR_QUEUE, replymessage)
            else:
                self.logger.error('Unsupported msg type for P4 controller: %s.' % msg.getMessageType())


if __name__ == '__main__':
    p4ctl = P4Controller(TURBONET_ZONE)
    p4ctl.run()