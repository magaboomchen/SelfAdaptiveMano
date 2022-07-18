#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.command import CMD_TYPE_GET_SFCI_STATE, CommandReply, CMD_TYPE_ADD_SFCI, CMD_TYPE_DEL_SFCI, \
    CMD_STATE_SUCCESSFUL, CMD_STATE_FAIL, CMD_STATE_PROCESSING
from sam.base.server import Server
from sam.base.messageAgent import SAMMessage, MessageAgent, VNF_CONTROLLER_QUEUE, \
    MSG_TYPE_VNF_CONTROLLER_CMD, MSG_TYPE_VNF_CONTROLLER_CMD_REPLY, MEDIATOR_QUEUE
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.vnf import VNFIStatus
from sam.serverController.vnfController.vcConfig import vcConfig
from sam.serverController.vnfController.vnfiAdder import VNFIAdder
from sam.serverController.vnfController.vnfiDeleter import VNFIDeleter
from sam.serverController.vnfController.vnfMaintainer import VNFIMaintainer, \
    VNFI_STATE_DEPLOYED, VNFI_STATE_FAILED
from sam.serverController.vnfController.sourceAllocator import SocketPortAllocator, SourceAllocator, CPUAllocator
from sam.serverController.vnfController.argParser import ArgParser
from sam.serverController.vnfController.vnfiStateMonitor import VNFIStateMonitor


class VNFController(object):
    def __init__(self, zoneName=""):
        logConf = LoggerConfigurator(__name__, './log', 'vnfController.log',
            level='debug')
        self.logger = logConf.getLogger()
        self.logger.info('Initialize vnf controller.')

        self.zoneName = zoneName

        self._commandsInfo = {}

        self._vnfiAdder = VNFIAdder(vcConfig.DOCKER_TCP_PORT, self.logger)
        self._vnfiDeleter = VNFIDeleter(vcConfig.DOCKER_TCP_PORT)

        self._vnfiMaintainer = VNFIMaintainer()
        self.vnfiStateMonitor = VNFIStateMonitor()

        self._vioManager = {}  # serverID: sourceAllocator for virtio
        self._cpuManager = {}  # serverID: sourceAllocator for CPU
        self._socketPortManager = {} # serverID: sourceAllocator for socket port

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
                resDict = {}
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
                elif cmd.cmdType == CMD_TYPE_GET_SFCI_STATE:
                    success, resDict = self._sfciStateMonitorHandler(cmd)
                    if success:
                        self._commandsInfo[cmd.cmdID]['state'] = CMD_STATE_SUCCESSFUL
                    else:
                        self._commandsInfo[cmd.cmdID]['state'] = CMD_STATE_FAIL
                else:
                    self.logger.error("Unsupported cmd type for vnf controller: %s." % cmd.cmdType)
                    self._commandsInfo[cmd.cmdID]['state'] = CMD_STATE_FAIL
                cmdRply = CommandReply(cmd.cmdID, self._commandsInfo[cmd.cmdID]['state'])
                cmdRply.attributes["zone"] = self.zoneName
                cmdRply.attributes.update(resDict)
                rplyMsg = SAMMessage(MSG_TYPE_VNF_CONTROLLER_CMD_REPLY, cmdRply)
                self._messageAgent.sendMsg(MEDIATOR_QUEUE, rplyMsg)
            else:
                self.logger.error('Unsupported msg type for vnf controller: %s.' % msg.getMessageType())

    def _sfciStateMonitorHandler(self, cmd):
        success = True
        resDict = {}
        try:
            sfcisDict = self._vnfiMaintainer.getAllSFCI()
            for sfciID, sfci in sfcisDict.items():
                vnfiSequence = sfci.vnfiSequence
                for vnfis in vnfiSequence:
                    for vnfi in vnfis:
                        if (type(vnfi.node) == Server
                                and self._vnfiMaintainer.hasVNFI(vnfi)):
                            vnfiDeployStatus = self._vnfiMaintainer.getVNFIDeployStatus(sfciID, vnfi)
                            vnfiState = self.vnfiStateMonitor.monitorVNFIHandler(vnfi, vnfiDeployStatus)
                            vnfi.vnfiStatus = VNFIStatus(state=vnfiState)
            resDict = {"sfcisDict":sfcisDict}
        except Exception as exp:
            ExceptionProcessor(self.logger).logException(exp, "Error occurs when get sfci state ")
            success = False
        return success, resDict

    def _sfciAddHandler(self, cmd):
        sfci = cmd.attributes['sfci']
        sfciID = sfci.sfciID
        self.logger.info('Adding sfci %s.' % sfciID)
        success = True
        if self._vnfiMaintainer.hasSFCI(sfciID):
            return success
        else:
            self._vnfiMaintainer.addSFCI(sfci)
        vnfSeq = cmd.attributes['sfci'].vnfiSequence
        for vnf in vnfSeq:
            for vnfi in vnf:
                if isinstance(vnfi.node, Server):
                    # self.logger.info('Adding vnfi %s.' % vnfi.vnfiID)
                    self.logger.info("Deploy vnfi {0} at node {1}".format(vnfi.vnfiID, vnfi.node.getServerID()))
                    if self._vnfiMaintainer.hasVNFI(vnfi):
                        # reassign an vnfi
                        self.logger.info("Reassign!")
                        continue
                    else:
                        self._vnfiMaintainer.addVNFI(sfciID, vnfi)

                    # get vioAllocator of server
                    serverID = vnfi.node.getServerID()
                    if serverID not in self._vioManager:
                        self._vioManager[serverID] = SourceAllocator(serverID, vcConfig.MAX_VIO_NUM)
                    vioAllo = self._vioManager[serverID]
                    if serverID not in self._cpuManager:
                        self._cpuManager[serverID] = CPUAllocator(serverID, vnfi.node.getCoreNUMADistribution(), notAvaiCPU=vcConfig.NOT_AVAI_CPU)
                    cpuAllo = self._cpuManager[serverID]
                    if serverID not in self._socketPortManager:
                        self._socketPortManager[serverID] = SocketPortAllocator(serverID)
                    socketPortAllo = self._socketPortManager[serverID]
                    try:
                        containerID, cpus, vioStart, controlSocketPort = self._vnfiAdder.addVNFI(vnfi, vioAllo, cpuAllo, socketPortAllo)
                        self._vnfiMaintainer.setVNFIState(sfciID, vnfi, VNFI_STATE_DEPLOYED)
                        self._vnfiMaintainer.setVNFIContainerID(sfciID, vnfi, containerID)
                        self._vnfiMaintainer.setVNFIVIOStart(sfciID, vnfi, vioStart)
                        self._vnfiMaintainer.setVNFICPU(sfciID, vnfi, cpus)
                        self._vnfiMaintainer.setVNFISocketPort(sfciID, vnfi, controlSocketPort)
                    except Exception as exp:
                        ExceptionProcessor(self.logger).logException(exp, "Error occurs when adding vnfi: ")
                        self.logger.error('Error occurs when adding vnfi: %s' % exp)
                        self._vnfiMaintainer.setVNFIState(sfciID, vnfi, VNFI_STATE_FAILED)
                        self._vnfiMaintainer.setVNFIError(sfciID, vnfi, exp)    
                        success = False
        return success

    def _sfciDeleteHandler(self, cmd):
        sfci = cmd.attributes['sfci']
        sfciID = sfci.sfciID
        self.logger.info('Deleting sfci %s.' % sfciID)
        try:
            sfciState = self._vnfiMaintainer.getSFCI(sfciID)
        except Exception as e:
            ExceptionProcessor(self.logger).logException(e, "SFCI not maintained in vnf controller.")
            self.logger.error('SFCI %s not maintained in vnf controller.' % sfciID)
            return False
        success = True
        for vnfiID in sfciState.keys():
            serverID = sfciState[vnfiID].vnfi.node.getServerID()
            try: 
                vioAllo = self._vioManager[serverID]
                cpuAllo = self._cpuManager[serverID]
                socketPortAllo = self._socketPortManager[serverID]
                self._vnfiDeleter.deleteVNFI(sfciState[vnfiID], vioAllo, cpuAllo, socketPortAllo)
                self._vnfiMaintainer.deleteVNFI(sfciID, vnfiID)
            except Exception as e:
                ExceptionProcessor(self.logger).logException(e, "Error occurs when deleting vnfi:")
                self.logger.error('Error occurs when deleting vnfi: %s' % e)
                success = False
        if success:
            self._vnfiMaintainer.deleteSFCI(sfci)
        return success 


if __name__=="__main__":
    argParser = ArgParser()
    zoneName = argParser.getArgs()['zoneName']   # example: None parameter
    vc = VNFController(zoneName)
    vc.startVNFController()