#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging

from sam.base.messageAgent import *
from sam.base.sfc import *
from sam.base.vnf import *
from sam.base.command import *
from sam.base.server import *
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.serverController.vnfController.vcConfig import vcConfig
from sam.serverController.vnfController.vnfiAdder import *
from sam.serverController.vnfController.vnfiDeleter import *
from sam.serverController.vnfController.vnfMaintainer import *
from sam.serverController.vnfController.sourceAllocator import *
from sam.serverController.vnfController.argParser import ArgParser

class VNFController(object):
    def __init__(self, zoneName=""):
        logConf = LoggerConfigurator(__name__, './log', 'vnfController.log',
            level='debug')
        self.logger = logConf.getLogger()
        self.logger.info('Initialize vnf controller.')

        self._commandsInfo = {}

        self._vnfiAdder = VNFIAdder(vcConfig.DOCKER_TCP_PORT)
        self._vnfiDeleter = VNFIDeleter(vcConfig.DOCKER_TCP_PORT)

        self._vnfiMaintainer = VNFIMaintainer()

        self._vioManager = {}  # serverID: sourceAllocator for virtio
        self._cpuManager = {}  # serverID: sourceAllocator for CPU

        self._messageAgent = MessageAgent()
        self.queueName = self._messageAgent.genQueueName(VNF_CONTROLLER_QUEUE, zoneName)
        self._messageAgent.startRecvMsg(self.queueName)

    def startVNFController(self):
        while True:
            msg = self._messageAgent.getMsg(self.queueName)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            elif msgType == MSG_TYPE_VNF_CONTROLLER_CMD:
                self.logger.info('Got a command.')
                cmd = msg.getbody()
                self._commandsInfo[cmd.cmdID] = {'cmd':cmd, 'state':CMD_STATE_PROCESSING}
                if cmd.cmdType == CMD_TYPE_ADD_SFCI:
                    success = self._sfciAddHandler(cmd)
                    if success:
                        self._commandsInfo[cmd.cmdID]['state'] = CMD_STATE_SUCCESSFUL
                    else:
                        self._commandsInfo[cmd.cmdID]['state'] = CMD_STATE_FAIL
                elif cmd.cmdType == CMD_TYPE_DEL_SFCI:
                    success = self._sfciDeleteHandler(cmd)
                    if success:
                        self._commandsInfo[cmd.cmdID]['state'] = CMD_STATE_SUCCESSFUL
                    else:
                        self._commandsInfo[cmd.cmdID]['state'] = CMD_STATE_FAIL
                else:
                    self.logger.error("Unsupported cmd type for vnf controller: %s." % cmd.cmdType)
                    self._commandsInfo[cmd.cmdID]['state'] = CMD_STATE_FAIL
                rplyMsg = SAMMessage(MSG_TYPE_VNF_CONTROLLER_CMD_REPLY,
                    CommandReply(cmd.cmdID, self._commandsInfo[cmd.cmdID]['state']))
                self._messageAgent.sendMsg(MEDIATOR_QUEUE, rplyMsg)
            else:
                self.logger.error('Unsupported msg type for vnf controller: %s.' % msg.getMessageType())

    def _sfciAddHandler(self, cmd):
        sfciID = cmd.attributes['sfci'].sfciID
        self.logger.info('Adding sfci %s.' % sfciID)
        # TODO: if sfciID in vnfMaintainer?
        self._vnfiMaintainer.addSFCI(sfciID)
        vnfSeq = cmd.attributes['sfci'].vnfiSequence
        success = True
        for vnf in vnfSeq:
            for vnfi in vnf:
                if isinstance(vnfi.node, Server):
                    # TODO: if vnfi in vnfMaintainer?
                    self.logger.info('Adding vnfi %s.' % vnfi.vnfiID)
                    self._vnfiMaintainer.addVNFI(sfciID, vnfi)

                    # get vioAllocator of server
                    serverID = vnfi.node.getServerID()
                    if serverID not in self._vioManager:
                        self._vioManager[serverID] = SourceAllocator(serverID, vcConfig.MAX_VIO_NUM)
                    vioAllo = self._vioManager[serverID]
                    if serverID not in self._cpuManager:
                        self._cpuManager[serverID] = CPUAllocator(serverID, vnfi.node.getCoreNUMADistribution(), notAvaiCPU=vcConfig.NOT_AVAI_CPU)
                    cpuAllo = self._cpuManager[serverID]
                    try:
                        containerID, cpus, vioStart = self._vnfiAdder.addVNFI(vnfi, vioAllo, cpuAllo)
                        self._vnfiMaintainer.setVNFIState(sfciID, vnfi, VNFI_STATE_DEPLOYED)
                        self._vnfiMaintainer.setVNFIContainerID(sfciID, vnfi, containerID)
                        self._vnfiMaintainer.setVNFIVIOStart(sfciID, vnfi, vioStart)
                        self._vnfiMaintainer.setVNFICPU(sfciID, vnfi, cpus)
                    except Exception as exp:
                        self.logger.error('Error occurs when adding vnfi: %s' % exp)
                        self._vnfiMaintainer.setVNFIState(sfciID, vnfi, VNFI_STATE_FAILED)
                        self._vnfiMaintainer.setVNFIError(sfciID, vnfi, exp)    
                        success = False
        return success

    def _sfciDeleteHandler(self, cmd):
        sfciID = cmd.attributes['sfci'].sfciID
        self.logger.info('Deleting sfci %s.' % sfciID)
        try:
            sfciState = self._vnfiMaintainer.getSFCI(sfciID)
        except Exception as e:
            self.logger.error('SFCI %s not maintained in vnf controller.' % sfciID)
            return False
        success = True
        for vnfiID in sfciState.keys():
            serverID = sfciState[vnfiID].vnfi.node.getServerID()
            try: 
                vioAllo = self._vioManager[serverID]
                cpuAllo = self._cpuManager[serverID]
                self._vnfiDeleter.deleteVNFI(sfciState[vnfiID], vioAllo, cpuAllo)
                self._vnfiMaintainer.deleteVNFI(sfciID, vnfiID)
            except Exception as e:
                self.logger.error('Error occurs when deleting vnfi: %s' % e)
                success = False
        if success:
            self._vnfiMaintainer.deleteSFCI(sfciID)
        return success 


if __name__=="__main__":
    argParser = ArgParser()
    zoneName = argParser.getArgs()['zoneName']   # example: None parameter
    vc = VNFController(zoneName)
    vc.startVNFController()