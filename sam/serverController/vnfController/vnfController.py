#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging

from sam.base.messageAgent import *
from sam.base.sfc import *
from sam.base.vnf import *
from sam.base.command import *
from sam.base.server import *
from sam.serverController.vnfController.vnfiAdder import *
from sam.serverController.vnfController.vnfiDeleter import *
from sam.serverController.vnfController.vnfMaintainer import *
from sam.serverController.vnfController.sourceAllocator import *

MAX_VIO_NUM = 65536
MAX_CPU_NUM = 12

# port for docker tcp connect
# (maybe unsafe, to modify in the future)
DOCKER_TCP_PORT = 5982

class VNFController(object):
    def __init__(self):
        logging.info('Initialize vnf controller.')

        self._commandsInfo = {}

        self._vnfiAdder = VNFIAdder(DOCKER_TCP_PORT)
        self._vnfiDeleter = VNFIDeleter(DOCKER_TCP_PORT)

        self._vnfiMaintainer = VNFIMaintainer()

        self._vioManager = {}  # serverID: sourceAllocator for virtio
        self._cpuManager = {}  # serverID: sourceAllocator for CPU

        self._messageAgent = MessageAgent()
        self._messageAgent.startRecvMsg(VNF_CONTROLLER_QUEUE)

    def startVNFController(self):
        while True:
            msg = self._messageAgent.getMsg(VNF_CONTROLLER_QUEUE)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            elif msgType == MSG_TYPE_VNF_CONTROLLER_CMD:
                logging.info('VNF controller get a command.')
                cmd = msg.getbody()
                self._commandsInfo[cmd.cmdID] = {'cmd':cmd, 'state':CMD_STATE_PROCESSING}
                if cmd.cmdType == CMD_TYPE_ADD_SFCI:
                    self._sfciAddHandler(cmd)
                    success = self._sfciAddHandler
                    if success:
                        self._commandsInfo[cmd.cmdID]['state'] = CMD_STATE_SUCCESSFUL
                    else:
                        self._commandsInfo[cmd.cmdID]['state'] = CMD_STATE_FAIL
                elif cmd.cmdType == CMD_TYPE_DEL_SFCI:
                    self._sfciDeleteHandler(cmd)
                    success = self._sfciDeleteHandler(cmd)
                    if success:
                        self._commandsInfo[cmd.cmdID]['state'] = CMD_STATE_SUCCESSFUL
                    else:
                        self._commandsInfo[cmd.cmdID]['state'] = CMD_STATE_FAIL
                else:
                    logging.error("Unsupported cmd type for vnf controller: %s." % cmd.cmdType)
                    self._commandsInfo[cmd.cmdID]['state'] = CMD_STATE_FAIL
                rplyMsg = SAMMessage(MSG_TYPE_VNF_CONTROLLER_CMD_REPLY,
                    CommandReply(cmd.cmdID, self._commandsInfo[cmd.cmdID]['state']))
                self._messageAgent.sendMsg(MEDIATOR_QUEUE, rplyMsg)
            else:
                logging.error('Unsupported msg type for vnf controller: %s.' % msg.getMessageType())

    def _sfciAddHandler(self, cmd):
        sfciID = cmd.attributes['sfci'].SFCIID
        logging.info('vnf controller add sfci %s' % sfciID)
        # TODO: if sfciID in vnfMaintainer?
        self._vnfiMaintainer.addSFCI(sfciID)
        vnfSeq = cmd.attributes['sfci'].VNFISequence
        success = True
        for vnf in vnfSeq:
            for vnfi in vnf:
                if isinstance(vnfi.node, Server):
                    # TODO: if vnfi in vnfMaintainer?
                    logging.info('vnf controller add vnfi')
                    self._vnfiMaintainer.addVNFI(sfciID, vnfi)

                    # get vioAllocator of server
                    serverID = vnfi.node.getServerID()
                    if serverID not in self._vioManager:
                        self._vioManager[serverID] = SourceAllocator(serverID, MAX_VIO_NUM)
                    vioAllo = self._vioManager[serverID]
                    if serverID not in self._cpuManager:
                        self._cpuManager[serverID] = SourceAllocator(serverID, MAX_CPU_NUM)
                    cpuAllo = self._cpuManager[serverID]
                    try:
                        containerID, cpuStart, vioStart = self._vnfiAdder.addVNFI(vnfi, vioAllo, cpuAllo)
                        self._vnfiMaintainer.setVNFIState(sfciID, vnfi, VNFI_STATE_DEPLOYED)
                        self._vnfiMaintainer.setVNFIContainerID(sfciID, vnfi, containerID)
                        self._vnfiMaintainer.setVNFIVIOStart(sfciID, vnfi, vioStart)
                        self._vnfiMaintainer.setVNFICPUStart(sfciID, vnfi, cpuStart)
                    except Exception as exp:
                        logging.info('error occurs in vnf controller when adding vnfi: %s' % exp)
                        self._vnfiMaintainer.setVNFIState(sfciID, vnfi, VNFI_STATE_FAILED)
                        self._vnfiMaintainer.setVNFIError(sfciID, vnfi, exp)    
                        success = False
        return success

    def _sfciDeleteHandler(self, cmd):
        sfciID = cmd.attributes['sfci'].SFCIID
        logging.info('vnf controller del sfci %s' % sfciID)
        try:
            sfciState = self._vnfiMaintainer.getSFCI(sfciID)
        except Exception as e:
            logging.error('SFCI %s not maintained in vnf controller.' % sfciID)
        return False
        success = True
        for vnfiID in sfciState.keys():
            serverID = sfciState[vnfiID].vnfi.node.getServerID()
            try: 
                vioAllo = self._vioManager[serverID]
                cpuAllo = self._cpuManager[serverID]
                self._vnfiDeleter.deleteVNFI(sfciState[vnfi], vioAllo, cpuAllo)
                self._vnfiMaintainer.deleteVNFI(sfciID, vnfiID)
            except Exception as e:
                logging.info('error occurs in vnf controller when deleting vnfi: %s' % exp)
                success = False
        if success:
            self._vnfiMaintainer.deleteSFCI(sfciID)
        return success 
            

if __name__=="__main__":
    logging.basicConfig(level=logging.INFO)
    vc = VNFController()
    vc.startVNFController()