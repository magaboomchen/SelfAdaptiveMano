#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid
import copy

from sam.base.messageAgent import MSG_TYPE_P4CONTROLLER_CMD, P4CONTROLLER_QUEUE, \
    PUFFER_ZONE, TURBONET_ZONE, MessageAgent, SAMMessage, SIMULATOR_ZONE, \
    MEDIATOR_QUEUE, MSG_TYPE_VNF_CONTROLLER_CMD, MSG_TYPE_SIMULATOR_CMD, \
    MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, SERVER_CLASSIFIER_CONTROLLER_QUEUE, \
    SIMULATOR_QUEUE, MSG_TYPE_NETWORK_CONTROLLER_CMD, NETWORK_CONTROLLER_QUEUE, \
    MSG_TYPE_SFF_CONTROLLER_CMD, SFF_CONTROLLER_QUEUE, VNF_CONTROLLER_QUEUE, \
    SERVER_MANAGER_QUEUE, MSG_TYPE_SERVER_MANAGER_CMD, MSG_TYPE_MEDIATOR_CMD_REPLY
from sam.base.switch import SWITCH_TYPE_NPOP
from sam.base.commandMaintainer import CommandMaintainer
from sam.base.command import CommandReply, CMD_TYPE_ADD_SFC, \
    CMD_TYPE_ADD_SFCI, CMD_TYPE_DEL_SFCI, CMD_TYPE_DEL_SFC, CMD_TYPE_GET_SERVER_SET, \
    CMD_TYPE_GET_TOPOLOGY, CMD_TYPE_GET_SFCI_STATE, CMD_STATE_PROCESSING, \
    CMD_STATE_WAITING, CMD_STATE_SUCCESSFUL, CMD_STATE_FAIL
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor


class Mediator(object):
    def __init__(self, mode):
        logConfigur = LoggerConfigurator(__name__, './log',
            'mediator.log', level='debug')
        self.logger = logConfigur.getLogger()
        self.logger.info("Init mediator.")

        self._cm = CommandMaintainer()
        self._mode = mode
        self._messageAgent = MessageAgent(self.logger)
        self._messageAgent.startRecvMsg(MEDIATOR_QUEUE)

    def startMediator(self):
        while True:
            try:        
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
                        self.logger.error("Unknown massage body")
            except Exception as ex:
                ExceptionProcessor(self.logger).logException(ex,
                    "mediator")

    def _commandHandler(self, cmd):
        self.logger.debug("Get a command")
        self._cm.addCmd(cmd)
        zone = cmd.attributes['zone']
        if zone == SIMULATOR_ZONE:
            # special case: simulator zone
            self._processCmdInSimulatorZone(cmd)
        elif zone == TURBONET_ZONE:
            # special case: turbonet zone
            self.logger.debug("Turbonet zone")
            self._processCmdInTurbonetZone(cmd)
        elif zone == PUFFER_ZONE:
            # default case: PUFFER zone
            self._processCmdInPufferZone(cmd)
        else:
            self.logger.error("Unknown zone {0}".format(zone))

    def _processCmdInSimulatorZone(self, cmd):
        self._forwardCmd2Simulator(cmd)

    def _processCmdInTurbonetZone(self, cmd):
        if cmd.cmdType == CMD_TYPE_ADD_SFC:
            self._addSFC2P4Controller(cmd)
        elif cmd.cmdType == CMD_TYPE_ADD_SFCI:
            self._addSFCI2SFFController(cmd)
            self._addSFCI2P4Controller(cmd)
            # skip self._addSFCIs2Server(cmd), because we need install 
            # entry to sff before install vnf.
            # prepare child cmd first
            self._prepareChildCmd(cmd, MSG_TYPE_VNF_CONTROLLER_CMD)
        elif cmd.cmdType == CMD_TYPE_DEL_SFCI:
            self._delSFCI4SFFController(cmd)
            self._delSFCI4P4Controller(cmd)
            self._delSFCIs4Server(cmd)
        elif cmd.cmdType == CMD_TYPE_DEL_SFC:
            self._delSFC2P4Controller(cmd)
        else:
            self._cm.delCmdwithChildCmd(cmd.cmdID)
            self.logger.error("Unkonwn command type.")

    def _processCmdInPufferZone(self, cmd):
        if cmd.cmdType == CMD_TYPE_ADD_SFC:
            # TODO: refactor classifier to support server based and P4 based according to the type of ingress/egress?
            # [X] Or just integrate all type of classifier in classifierController.
            # decouple selection from mediator to classifierController.
            if self._mode['classifierType'] == 'Server':
                self._addSFC2ClassifierController(cmd)
            # time.sleep(3)   # TODO: refactor this hardcode function: after add sfc to classifier, add sfc 2 netowrk controller
            self._addSFC2NetworkController(cmd)
        elif cmd.cmdType == CMD_TYPE_ADD_SFCI:
            if self._mode['classifierType'] == 'Server':
                self._addSFCI2ClassifierController(cmd)
            self._addSFCI2SFFController(cmd)
            # time.sleep(3)   # TODO: refactor this hardcode function: after add sfc to classifier, add sfc 2 netowrk controller
            self._addSFCI2NetworkController(cmd)
            # skip self._addSFCIs2Server(cmd), because we need install 
            # entry to sff before install vnf.
            # prepare child cmd first
            self._prepareChildCmd(cmd, MSG_TYPE_VNF_CONTROLLER_CMD)
        elif cmd.cmdType == CMD_TYPE_DEL_SFCI:
            if self._mode['classifierType'] == 'Server':
                self._delSFCI4ClassifierController(cmd)
            self._delSFCI4SFFController(cmd)
            self._delSFCI4NetworkController(cmd)
            self._delSFCIs4Server(cmd)
        elif cmd.cmdType == CMD_TYPE_DEL_SFC:
            if self._mode['classifierType'] == 'Server':
                self._delSFC4ClassifierController(cmd)
            self._delSFC4NetworkController(cmd)
        elif cmd.cmdType == CMD_TYPE_GET_SERVER_SET:
            self.logger.debug("Get CMD_TYPE_GET_SERVER_SET")
            self._getServerSet4ServerManager(cmd)
        elif cmd.cmdType == CMD_TYPE_GET_TOPOLOGY:
            self.logger.debug("Get CMD_TYPE_GET_TOPOLOGY")
            self._getTopo4NetworkController(cmd)
        elif cmd.cmdType == CMD_TYPE_GET_SFCI_STATE:
            self.logger.debug("Get CMD_TYPE_GET_SFCI_STATE")
            # self._getSFCIStatus4SFFP4(cmd)
            self._getSFCIStatus4SFF(cmd)
        else:
            self._cm.delCmdwithChildCmd(cmd.cmdID)
            self.logger.error("Unkonwn command type.")

    def _prepareChildCmd(self, cmd, cCmdName):
        cmdID = cmd.cmdID
        # generate a child command
        cCmd = copy.deepcopy(cmd)
        cCmdID = uuid.uuid1()
        cCmd.cmdID = cCmdID
        # add it to commands maintainer
        self._cm.addChildCmd2Cmd(cmdID, cCmdName, cCmdID)
        self._cm.addCmd(cCmd)
        self._cm.addParentCmd2Cmd(cCmdID, cmdID)
        return cCmd

    def forwardCmd(self, cmd, msgType, queue):
        msg = SAMMessage(msgType, cmd)
        self._messageAgent.sendMsg(queue, msg)

    def _forwardCmd2Simulator(self, cmd):
        cCmd = self._prepareChildCmd(cmd, MSG_TYPE_SIMULATOR_CMD)
        self.forwardCmd(cCmd, MSG_TYPE_SIMULATOR_CMD, SIMULATOR_QUEUE)
        self._cm.transitCmdState(cmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)
        self._cm.transitCmdState(cCmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)

    def _addSFC2ClassifierController(self, cmd):
        cCmd = self._prepareChildCmd(cmd, MSG_TYPE_CLASSIFIER_CONTROLLER_CMD)
        zoneName = cmd.attributes['zone']
        queueName = self._messageAgent.genQueueName(
            SERVER_CLASSIFIER_CONTROLLER_QUEUE, zoneName)
        self.forwardCmd(cCmd, MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, queueName)
        self._cm.transitCmdState(cmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)
        self._cm.transitCmdState(cCmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)

    def _addSFCI2ClassifierController(self, cmd):
        cCmd = self._prepareChildCmd(cmd, MSG_TYPE_CLASSIFIER_CONTROLLER_CMD)
        zoneName = cmd.attributes['zone']
        queueName = self._messageAgent.genQueueName(
            SERVER_CLASSIFIER_CONTROLLER_QUEUE, zoneName)
        self.forwardCmd(cCmd, MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, queueName)
        self._cm.transitCmdState(cmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)
        self._cm.transitCmdState(cCmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)

    def _addSFC2NetworkController(self, cmd):
        cCmd = self._prepareChildCmd(cmd, MSG_TYPE_NETWORK_CONTROLLER_CMD)
        zoneName = cmd.attributes['zone']
        queueName = self._messageAgent.genQueueName(
            NETWORK_CONTROLLER_QUEUE, zoneName)
        self.forwardCmd(cCmd, MSG_TYPE_NETWORK_CONTROLLER_CMD, queueName)
        self._cm.transitCmdState(cmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)
        self._cm.transitCmdState(cCmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)

    def _addSFC2P4Controller(self, cmd):
        cCmd = self._prepareChildCmd(cmd, MSG_TYPE_P4CONTROLLER_CMD)
        zoneName = cmd.attributes['zone']
        queueName = self._messageAgent.genQueueName(
            P4CONTROLLER_QUEUE, zoneName)
        self.logger.debug("queueName is {0}".format(queueName))
        self.forwardCmd(cCmd, MSG_TYPE_P4CONTROLLER_CMD, queueName)
        self._cm.transitCmdState(cmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)
        self._cm.transitCmdState(cCmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)

    def _addSFCI2P4Controller(self, cmd):
        cCmd = self._prepareChildCmd(cmd, MSG_TYPE_P4CONTROLLER_CMD)
        zoneName = cmd.attributes['zone']
        queueName = self._messageAgent.genQueueName(
            P4CONTROLLER_QUEUE, zoneName)
        self.forwardCmd(cCmd, MSG_TYPE_P4CONTROLLER_CMD, queueName)
        self._cm.transitCmdState(cmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)
        self._cm.transitCmdState(cCmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)

    def _delSFCI4P4Controller(self, cmd):
        cCmd = self._prepareChildCmd(cmd, MSG_TYPE_P4CONTROLLER_CMD)
        zoneName = cmd.attributes['zone']
        queueName = self._messageAgent.genQueueName(
            P4CONTROLLER_QUEUE, zoneName)
        self.forwardCmd(cCmd, MSG_TYPE_P4CONTROLLER_CMD, queueName)
        self._cm.transitCmdState(cmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)
        self._cm.transitCmdState(cCmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)

    def _addSFCI2NetworkController(self, cmd):
        cCmd = self._prepareChildCmd(cmd, MSG_TYPE_NETWORK_CONTROLLER_CMD)
        zoneName = cmd.attributes['zone']
        queueName = self._messageAgent.genQueueName(
            NETWORK_CONTROLLER_QUEUE, zoneName)
        self.forwardCmd(cCmd, MSG_TYPE_NETWORK_CONTROLLER_CMD, queueName)
        self._cm.transitCmdState(cmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)
        self._cm.transitCmdState(cCmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)

    def _addSFCI2SFFController(self, cmd):
        cCmd = self._prepareChildCmd(cmd, MSG_TYPE_SFF_CONTROLLER_CMD)
        zoneName = cmd.attributes['zone']
        queueName = self._messageAgent.genQueueName(
            SFF_CONTROLLER_QUEUE, zoneName)
        self.forwardCmd(cCmd, MSG_TYPE_SFF_CONTROLLER_CMD, queueName)
        self._cm.transitCmdState(cmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)
        self._cm.transitCmdState(cCmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)

    def _addSFCIs2Server(self, cmd):
        cCmd = self._cm.getChildCmd(cmd.cmdID, MSG_TYPE_VNF_CONTROLLER_CMD)
        zoneName = cmd.attributes['zone']
        queueName = self._messageAgent.genQueueName(
                        VNF_CONTROLLER_QUEUE, zoneName)
        self.logger.debug("queueName is {0}".format(queueName))
        state = self._cm.getCmdState(cCmd.cmdID)
        if state == CMD_STATE_WAITING:
            cCmd.attributes['source'] = "unknown"
            self.logger.debug("send a cmd to vnfController.")
            self.forwardCmd(cCmd, MSG_TYPE_VNF_CONTROLLER_CMD, queueName)
            self._cm.transitCmdState(cmd.cmdID, CMD_STATE_WAITING,
                CMD_STATE_PROCESSING)
            self._cm.transitCmdState(cCmd.cmdID, CMD_STATE_WAITING,
                CMD_STATE_PROCESSING)
        else:
            self.logger.error("_addSFCIs2Server's cCmd state: {0}".format(
                state))

    def _delSFCIs4Server(self, cmd):
        cCmd = self._prepareChildCmd(cmd, MSG_TYPE_VNF_CONTROLLER_CMD)
        zoneName = cmd.attributes['zone']
        queueName = self._messageAgent.genQueueName(
            VNF_CONTROLLER_QUEUE, zoneName)
        self.forwardCmd(cCmd, MSG_TYPE_VNF_CONTROLLER_CMD, queueName)
        self._cm.transitCmdState(cmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)
        self._cm.transitCmdState(cCmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)

    def _delSFC4NetworkController(self, cmd):
        cCmd = self._prepareChildCmd(cmd, MSG_TYPE_NETWORK_CONTROLLER_CMD)
        zoneName = cmd.attributes['zone']
        queueName = self._messageAgent.genQueueName(
            NETWORK_CONTROLLER_QUEUE, zoneName)
        self.forwardCmd(cCmd, MSG_TYPE_NETWORK_CONTROLLER_CMD, queueName)
        self._cm.transitCmdState(cmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)
        self._cm.transitCmdState(cCmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)

    def _delSFC2P4Controller(self, cmd):
        cCmd = self._prepareChildCmd(cmd, MSG_TYPE_P4CONTROLLER_CMD)
        zoneName = cmd.attributes['zone']
        queueName = self._messageAgent.genQueueName(
            P4CONTROLLER_QUEUE, zoneName)
        self.forwardCmd(cCmd, MSG_TYPE_P4CONTROLLER_CMD, queueName)
        self._cm.transitCmdState(cmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)
        self._cm.transitCmdState(cCmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)

    def _delSFCI4NetworkController(self, cmd):
        cCmd = self._prepareChildCmd(cmd, MSG_TYPE_NETWORK_CONTROLLER_CMD)
        zoneName = cmd.attributes['zone']
        queueName = self._messageAgent.genQueueName(
            NETWORK_CONTROLLER_QUEUE, zoneName)
        self.forwardCmd(cCmd, MSG_TYPE_NETWORK_CONTROLLER_CMD, queueName)
        self._cm.transitCmdState(cmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)
        self._cm.transitCmdState(cCmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)

    def _delSFC4ClassifierController(self, cmd):
        cCmd = self._prepareChildCmd(cmd, MSG_TYPE_CLASSIFIER_CONTROLLER_CMD)
        zoneName = cmd.attributes['zone']
        queueName = self._messageAgent.genQueueName(
            SERVER_CLASSIFIER_CONTROLLER_QUEUE, zoneName)
        self.forwardCmd(cCmd, MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, queueName)
        self._cm.transitCmdState(cmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)
        self._cm.transitCmdState(cCmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)

    def _delSFCI4ClassifierController(self, cmd):
        cCmd = self._prepareChildCmd(cmd, MSG_TYPE_CLASSIFIER_CONTROLLER_CMD)
        zoneName = cmd.attributes['zone']
        queueName = self._messageAgent.genQueueName(
            SERVER_CLASSIFIER_CONTROLLER_QUEUE, zoneName)
        self.forwardCmd(cCmd, MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, queueName)
        self._cm.transitCmdState(cmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)
        self._cm.transitCmdState(cCmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)

    def _delSFCI4SFFController(self, cmd):
        cCmd = self._prepareChildCmd(cmd, MSG_TYPE_SFF_CONTROLLER_CMD)
        zoneName = cmd.attributes['zone']
        queueName = self._messageAgent.genQueueName(
            SFF_CONTROLLER_QUEUE, zoneName)
        self.forwardCmd(cCmd, MSG_TYPE_SFF_CONTROLLER_CMD, queueName)
        self._cm.transitCmdState(cmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)
        self._cm.transitCmdState(cCmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)

    def _getServerSet4ServerManager(self, cmd):
        cCmd = self._prepareChildCmd(cmd, MSG_TYPE_SERVER_MANAGER_CMD)
        zoneName = cmd.attributes['zone']
        queueName = self._messageAgent.genQueueName(
            SERVER_MANAGER_QUEUE, zoneName)
        self.forwardCmd(cCmd, MSG_TYPE_SERVER_MANAGER_CMD, queueName)
        self._cm.transitCmdState(cmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)
        self._cm.transitCmdState(cCmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)

    def _getTopo4NetworkController(self, cmd):
        cCmd = self._prepareChildCmd(cmd, MSG_TYPE_NETWORK_CONTROLLER_CMD)
        zoneName = cmd.attributes['zone']
        queueName = self._messageAgent.genQueueName(
            NETWORK_CONTROLLER_QUEUE, zoneName)
        self.forwardCmd(cCmd, MSG_TYPE_NETWORK_CONTROLLER_CMD, queueName)
        self._cm.transitCmdState(cmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)
        self._cm.transitCmdState(cCmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)

    def _getSFCIStatus4SFF(self, cmd):
        cCmd = self._prepareChildCmd(cmd, MSG_TYPE_SFF_CONTROLLER_CMD)
        zoneName = cmd.attributes['zone']
        queueName = self._messageAgent.genQueueName(
            SFF_CONTROLLER_QUEUE, zoneName)
        self.forwardCmd(cCmd, MSG_TYPE_SFF_CONTROLLER_CMD, queueName)
        self._cm.transitCmdState(cmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)
        self._cm.transitCmdState(cCmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)

    def _getSFCIStatus4SFFP4(self, cmd):
        cCmd = self._prepareChildCmd(cmd, MSG_TYPE_SFF_CONTROLLER_CMD)
        zoneName = cmd.attributes['zone']
        queueName = self._messageAgent.genQueueName(
            SFF_CONTROLLER_QUEUE, zoneName)
        self.forwardCmd(cCmd, MSG_TYPE_SFF_CONTROLLER_CMD, queueName)
        self._cm.transitCmdState(cmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)
        self._cm.transitCmdState(cCmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)

        cCmd = self._prepareChildCmd(cmd, MSG_TYPE_NETWORK_CONTROLLER_CMD)
        zoneName = cmd.attributes['zone']
        queueName = self._messageAgent.genQueueName(
            NETWORK_CONTROLLER_QUEUE, zoneName)
        self.forwardCmd(cCmd, MSG_TYPE_NETWORK_CONTROLLER_CMD, queueName)
        self._cm.transitCmdState(cmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)
        self._cm.transitCmdState(cCmd.cmdID, CMD_STATE_WAITING,
            CMD_STATE_PROCESSING)

    def _commandReplyHandler(self, cmdRply):
        # update cmd state
        cmdID = cmdRply.cmdID
        state = cmdRply.cmdState
        if self._cm.isChildCmdHasCmdRply(cmdID) == True:
            self.logger.warning("Get duplicated cmd reply")
            return 
        self._cm.changeCmdState(cmdID,state)
        self._cm.addCmdRply(cmdID,cmdRply)
        # debug
        cmd = self._cm.getCmd(cmdID)
        self.logger.debug("cmdRply attributes: {0}".format(
            cmdRply.attributes.keys()))
        if 'source' in cmdRply.attributes:
            self.logger.debug(
                "get cmd reply, cmdID:{0}, cmdType:{1}, source:{2}.".format(
                    cmdID, cmd.cmdType, cmdRply.attributes['source']))
        for keys, value in self._cm._commandsInfo.items():
            self.logger.debug(
                "cmdID: {0}, cmdType:{1}, state: {2}, parentCmdID: {3}, childCmdID: {4}".format(
                    keys, value['cmd'].cmdType,
                    value['state'], value['parentCmdID'], value['childCmdID']))
        # execute state transfer action
        self._exeCmdStateAction(cmdID)

    def _exeCmdStateAction(self, cmdID):
        parentCmdID = self._cm.getParentCmdID(cmdID)
        dstQueueName = self._cm.getCmd(parentCmdID).attributes['source']
        if self._cm.isParentCmdSuccessful(parentCmdID):
            self.logger.info("Command {0} is successful".format(parentCmdID))
            self._cm.changeCmdState(parentCmdID, CMD_STATE_SUCCESSFUL)
            cmdRply = self._genParentCmdRply(parentCmdID,
                                                CMD_STATE_SUCCESSFUL)
            self.logger.debug("successful command reply to {0}".format(dstQueueName))
            self._sendParentCmdRply(cmdRply, dstQueueName)
        elif self._cm.isParentCmdFailed(parentCmdID):
            # if mediator haven't send cmd rply, send cmd rply
            if self._cm.isOnlyOneChildCmdFailed(parentCmdID) and \
                self._cm.getCmdState(cmdID) == CMD_STATE_FAIL:
                # debug
                cmdInfo = self._cm._commandsInfo[parentCmdID]
                self.logger.debug("A command failed. Here are details:")
                for key, childCmdID in cmdInfo['childCmdID'].items():
                    if self._cm.getCmdState(childCmdID) == CMD_STATE_FAIL:
                        self.logger.debug("childCmdID: {0}".format(childCmdID))
                # workflow
                self._cm.changeCmdState(parentCmdID, CMD_STATE_FAIL)
                cmdRply = self._genParentCmdRply(parentCmdID,
                    CMD_STATE_FAIL)
                self._sendParentCmdRply(cmdRply, dstQueueName)
                self.logger.debug("send cmd rply")
        elif self._cm.isParentCmdWaiting(parentCmdID):
            self._waitingParentCmdHandler(parentCmdID)
        else:
            pass

        if self._cm.isAllChildCmdDetermined(parentCmdID):
            self._cm.delCmdwithChildCmd(parentCmdID)

    def _genParentCmdRply(self, parentCmdID, state):
        cCmdRplyList = self._cm.getChildCMdRplyList(parentCmdID)
        attr = self._getMixedAttributes(cCmdRplyList)
        return CommandReply(parentCmdID,state,attr)

    def _getMixedAttributes(self, cCmdRplyList):
        attributes = {}
        for cmdRply in cCmdRplyList:
            if self._messageAgent.isCommandReply(cmdRply):
                attr = cmdRply.attributes
                for key, value in attr.items():
                    if key not in attributes.keys():
                        attributes[key] = attr[key]
                    else:
                        if type(value) == dict:
                            self._MergeDict(value, attributes[key])
                        else:
                            assert value == attributes[key]
                            self.logger.debug("attr value is {0}".format(value))
        return attributes

    def _MergeDict(self, dict1, dict2):
        return (dict2.update(dict1))

    def _sendParentCmdRply(self, cmdRply, dstQueueName):
        # Decide the queue
        cmdRplyType = self._cm.getCmdType(cmdRply.cmdID)
        if cmdRplyType == CMD_TYPE_ADD_SFC or \
                cmdRplyType == CMD_TYPE_ADD_SFCI or \
                cmdRplyType == CMD_TYPE_DEL_SFCI or\
                cmdRplyType == CMD_TYPE_DEL_SFC :
            # queue = ORCHESTRATOR_QUEUE
            queue = dstQueueName
        elif cmdRplyType == CMD_TYPE_GET_SERVER_SET or \
                cmdRplyType == CMD_TYPE_GET_TOPOLOGY or \
                cmdRplyType == CMD_TYPE_GET_SFCI_STATE:
            raise ValueError("Measurer use gRPC to collect information.")
        else:
            self.logger.error("Command reply error.")
        # generate message
        cmdRplyMsg = SAMMessage(MSG_TYPE_MEDIATOR_CMD_REPLY,
            cmdRply)
        self._messageAgent.sendMsg(queue, cmdRplyMsg)

    def _waitingParentCmdHandler(self,parentCmdID):
        if self._cm.getCmdType(parentCmdID) == CMD_TYPE_ADD_SFCI:
            sffState = self._cm.getChildCmdState(parentCmdID,
                MSG_TYPE_SFF_CONTROLLER_CMD)
            if sffState == CMD_STATE_SUCCESSFUL:
                cmd = self._cm.getCmd(parentCmdID)
                self._addSFCIs2Server(cmd)


if __name__=="__main__":
    mode = {
        'switchType': SWITCH_TYPE_NPOP,
        'classifierType': 'Server'  # 'Switch'
    }
    m = Mediator(mode)
    m.startMediator()
