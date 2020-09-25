#!/usr/bin/python
# -*- coding: UTF-8 -*-

import base64
import time
import uuid
import subprocess
import logging
import struct
import copy

import pickle

from sam.base.server import Server
from sam.base.messageAgent import *
from sam.base.switch import *
from sam.base.sfc import *
from sam.base.command import *


class Mediator(object):
    def __init__(self, mode):
        logging.info("Init mediator.")
        self._cm = CommandMaintainer()
        self._mode = mode
        self._messageAgent = MessageAgent()
        self._messageAgent.startRecvMsg(MEDIATOR_QUEUE)

    def startMediator(self):
        while True:
            msg = self._messageAgent.getMsg(MEDIATOR_QUEUE)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            else:
                body = msg.getbody()
                if self._messageAgent.isCommand(body):
                    self._commandHandler(body)
                elif self._messageAgent.isCommandReply(body):
                    self._commandReplyHandler(body)
                else:
                    logging.error("Unknown massage body")

    def _commandHandler(self,cmd):
        logging.debug("Get a command")
        self._cm.addCmd(cmd)
        if cmd.cmdType == CMD_TYPE_ADD_SFCI:
            if self._mode['classifierType'] == 'Server':
                self._addSFCI2ClassifierController(cmd)
            self._addSFCI2NetworkController(cmd)
            self._addSFCI2BessController(cmd)
            # wait for the cmdReply from bess sff
            self._prepareChildCmd(cmd,MSG_TYPE_SERVER_MANAGER_CMD)
            # skip self._addSFCIs2Server(cmd), because we need install bess
            # before install vnf.
        elif cmd.cmdType == CMD_TYPE_DEL_SFCI:
            if self._mode['classifierType'] == 'Server':
                self._delSFCI4ClassifierController(cmd)
            self._delSFCI4BessController(cmd)
            self._delSFCI4NetworkController(cmd)
            self._delSFCIs4Server(cmd)
        elif cmd.cmdType == CMD_TYPE_GET_SERVER_SET:
            logging.debug("Get CMD_TYPE_GET_SERVER_SET")
            self._getServerSet4ServerManager(cmd)
        elif cmd.cmdType == CMD_TYPE_GET_TOPOLOGY:
            logging.debug("Get CMD_TYPE_GET_TOPOLOGY")
            self._getTopo4NetworkController(cmd)
        elif cmd.cmdType == CMD_TYPE_GET_SFCI_STATE:
            logging.debug("Get CMD_TYPE_GET_SFCI_STATE")
            # self._getSFCIStatus4ServerP4(cmd)
            self._getSFCIStatus4SFF(cmd)
        else:
            self._cm.delCmdwithChildCmd(cmd.cmdID)
            logging.error("Unkonwn command type.")

    def _prepareChildCmd(self,cmd,cCmdName):
        cmdID = cmd.cmdID
        # generate a child command
        cCmd = copy.deepcopy(cmd)
        cCmdID = uuid.uuid1()
        cCmd.cmdID = cCmdID
        # add it to commands maintainer
        self._cm.addChildCmd2Cmd(cmdID,cCmdName,cCmdID)
        self._cm.addCmd(cCmd)
        self._cm.addParentCmd2Cmd(cCmdID,cmdID)
        return cCmd

    def forwardCmd(self,cmd,msgType,queue):
        msg = SAMMessage(msgType, cmd)
        self._messageAgent.sendMsg(queue,msg)

    def _addSFCI2ClassifierController(self,cmd):
        cCmd = self._prepareChildCmd(cmd,MSG_TYPE_CLASSIFIER_CONTROLLER_CMD)
        self.forwardCmd(cCmd,MSG_TYPE_CLASSIFIER_CONTROLLER_CMD,
            SERVER_CLASSIFIER_CONTROLLER_QUEUE)
        self._cm.changeCmdState(cmd.cmdID,CMD_STATE_PROCESSING)

    def _addSFCI2NetworkController(self,cmd):
        cCmd = self._prepareChildCmd(cmd,MSG_TYPE_NETWORK_CONTROLLER_CMD)
        self.forwardCmd(cCmd,MSG_TYPE_NETWORK_CONTROLLER_CMD,
            NETWORK_CONTROLLER_QUEUE)
        self._cm.changeCmdState(cmd.cmdID,CMD_STATE_PROCESSING)

    def _addSFCI2BessController(self,cmd):
        cCmd = self._prepareChildCmd(cmd,MSG_TYPE_SSF_CONTROLLER_CMD)
        self.forwardCmd(cCmd,MSG_TYPE_SSF_CONTROLLER_CMD,
            SFF_CONTROLLER_QUEUE)
        self._cm.changeCmdState(cmd.cmdID,CMD_STATE_PROCESSING)

    def _addSFCIs2Server(self,cmd):
        cCmd = self._prepareChildCmd(cmd,MSG_TYPE_SERVER_MANAGER_CMD)
        self.forwardCmd(cCmd,MSG_TYPE_SERVER_MANAGER_CMD,
            VNF_CONTROLLER_QUEUE)
        self._cm.changeCmdState(cmd.cmdID,CMD_STATE_PROCESSING)

    def _delSFCIs4Server(self,cmd):
        cCmd = self._prepareChildCmd(cmd,MSG_TYPE_SERVER_MANAGER_CMD)
        self.forwardCmd(cCmd,MSG_TYPE_SERVER_MANAGER_CMD,
            SERVER_MANAGER_QUEUE)
        self._cm.changeCmdState(cmd.cmdID,CMD_STATE_PROCESSING)

    def _delSFCI4NetworkController(self,cmd):
        cCmd = self._prepareChildCmd(cmd,MSG_TYPE_NETWORK_CONTROLLER_CMD)
        self.forwardCmd(cCmd,MSG_TYPE_NETWORK_CONTROLLER_CMD,
            NETWORK_CONTROLLER_QUEUE)
        self._cm.changeCmdState(cmd.cmdID,CMD_STATE_PROCESSING)

    def _delSFCI4ClassifierController(self,cmd):
        cCmd = self._prepareChildCmd(cmd,MSG_TYPE_CLASSIFIER_CONTROLLER_CMD)
        self.forwardCmd(cCmd,MSG_TYPE_CLASSIFIER_CONTROLLER_CMD,
            SERVER_CLASSIFIER_CONTROLLER_QUEUE)
        self._cm.changeCmdState(cmd.cmdID,CMD_STATE_PROCESSING)

    def _delSFCI4BessController(self,cmd):
        cCmd = self._prepareChildCmd(cmd,MSG_TYPE_SSF_CONTROLLER_CMD)
        self.forwardCmd(cCmd,MSG_TYPE_SSF_CONTROLLER_CMD,
            SFF_CONTROLLER_QUEUE)
        self._cm.changeCmdState(cmd.cmdID,CMD_STATE_PROCESSING)

    def _getServerSet4ServerManager(self,cmd):
        cCmd = self._prepareChildCmd(cmd,MSG_TYPE_SERVER_MANAGER_CMD)
        self.forwardCmd(cCmd,MSG_TYPE_SERVER_MANAGER_CMD,
            SERVER_MANAGER_QUEUE)
        self._cm.changeCmdState(cmd.cmdID,CMD_STATE_PROCESSING)

    def _getTopo4NetworkController(self,cmd):
        cCmd = self._prepareChildCmd(cmd,MSG_TYPE_NETWORK_CONTROLLER_CMD)
        self.forwardCmd(cCmd,MSG_TYPE_NETWORK_CONTROLLER_CMD,
            NETWORK_CONTROLLER_QUEUE)
        self._cm.changeCmdState(cmd.cmdID,CMD_STATE_PROCESSING)

    def _getSFCIStatus4SFF(self, cmd):
        cCmd = self._prepareChildCmd(cmd, MSG_TYPE_SSF_CONTROLLER_CMD)
        self.forwardCmd(cCmd, MSG_TYPE_SSF_CONTROLLER_CMD,
            SFF_CONTROLLER_QUEUE)
        self._cm.changeCmdState(cmd.cmdID, CMD_STATE_PROCESSING)

    def _getSFCIStatus4ServerP4(self,cmd):
        cCmd = self._prepareChildCmd(cmd, MSG_TYPE_SSF_CONTROLLER_CMD)
        self.forwardCmd(cCmd, MSG_TYPE_SSF_CONTROLLER_CMD,
            SFF_CONTROLLER_QUEUE)
        self._cm.changeCmdState(cmd.cmdID, CMD_STATE_PROCESSING)

        cCmd = self._prepareChildCmd(cmd,MSG_TYPE_NETWORK_CONTROLLER_CMD)
        self.forwardCmd(cCmd,MSG_TYPE_NETWORK_CONTROLLER_CMD,
            NETWORK_CONTROLLER_QUEUE)
        self._cm.changeCmdState(cmd.cmdID,CMD_STATE_PROCESSING)

    def _commandReplyHandler(self,cmdRply):
        # update cmd state
        cmdID = cmdRply.cmdID
        state = cmdRply.cmdState
        self._cm.changeCmdState(cmdID,state)
        self._cm.addCmdRply(cmdID,cmdRply)
        # execute state transfer action
        self._exeCmdStateAction(cmdID)

    def _exeCmdStateAction(self,cmdID):
        parentCmdID = self._cm.getParentCmdID(cmdID)
        # if all child cmd is successful, then send cmdRply
        if self._cm.isParentCmdSuccessful(parentCmdID):
            self._cm.changeCmdState(parentCmdID, CMD_STATE_SUCCESSFUL)
            cmdRply = self._genParentCmdRply(parentCmdID,
                CMD_STATE_SUCCESSFUL)
            self._sendParentCmdRply(cmdRply)
            self._cm.delCmdwithChildCmd(parentCmdID)
        elif self._cm.isParentCmdFailed(parentCmdID):
            self._cm.changeCmdState(parentCmdID, CMD_STATE_FAIL)
            cmdRply = self._genParentCmdRply(parentCmdID,
                CMD_STATE_FAIL)
            self._sendParentCmdRply(cmdRply)
        elif self._cm.isParentCmdWaiting(parentCmdID):
            self._waitingParentCmdHandler(parentCmdID)
        else:
            pass

    def _genParentCmdRply(self,parentCmdID,state):
        cCmdRplyList = self._cm.getChildCMdRplyList(parentCmdID)
        attr = self._getMixedAttributes(cCmdRplyList)
        return CommandReply(parentCmdID,state,attr)

    def _getMixedAttributes(self,cCmdRplyList):
        attributes = {}
        for cmdRply in cCmdRplyList:
            if self._messageAgent.isCommandReply(cmdRply):
                attr = cmdRply.attributes
                for key in attr.iterkeys():
                    if not key in attributes.iterkeys():
                        attributes[key] = attr[key]
                    else:
                        self._MergeDict(attr[key],attributes[key])
        return attributes

    def _MergeDict(self,dict1,dict2):
        return (dict2.update(dict1))

    def _sendParentCmdRply(self,cmdRply):
        # Decide the queue
        cmdRplyType = self._cm.getCmdType(cmdRply.cmdID)
        if cmdRplyType == CMD_TYPE_ADD_SFCI or \
            cmdRplyType == CMD_TYPE_DEL_SFCI:
            queue = ORCHESTRATOR_QUEUE
        elif cmdRplyType == CMD_TYPE_GET_SERVER_SET or\
            cmdRplyType == CMD_TYPE_GET_TOPOLOGY or\
            cmdRplyType == CMD_TYPE_GET_SFCI_STATE:
            queue = MEASURER_QUEUE
        else:
            logging.error("Command reply error.")
        # generate message
        cmdRplyMsg = SAMMessage(MSG_TYPE_MEDIATOR_CMD_REPLY,
            cmdRply)
        self._messageAgent.sendMsg(queue,cmdRplyMsg)

    def _waitingParentCmdHandler(self,parentCmdID):
        if self._cm.getCmdType(parentCmdID) == CMD_TYPE_ADD_SFCI:
            bessState = self._cm.getChildCmdState(parentCmdID,
                MSG_TYPE_SSF_CONTROLLER_CMD)
            logging.debug("wating check______")
            if bessState == CMD_STATE_SUCCESSFUL:
                cmd = self._cm.getCmd(parentCmdID)
                self._addSFCIs2Server(cmd)


if __name__=="__main__":
    logging.basicConfig(level=logging.INFO)
    mode = {
        'switchType': SWITCH_TYPE_TOR,
        'classifierType': 'Server'  # 'Switch'
    }
    m = Mediator(mode)
    m.startMediator()

