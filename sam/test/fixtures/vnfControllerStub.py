#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging
from sam.base.command import CMD_STATE_SUCCESSFUL, CommandReply
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.loggerConfigurator import LoggerConfigurator

from sam.base.messageAgent import TURBONET_ZONE, SAMMessage, MessageAgent, MEDIATOR_QUEUE, \
    MSG_TYPE_VNF_CONTROLLER_CMD_REPLY
from sam.base.messageAgentAuxillary.msgAgentRPCConf import VNF_CONTROLLER_IP, VNF_CONTROLLER_PORT
from sam.base.sfc import SFCI
from sam.base.slo import SLO
from sam.base.sshAgent import SSHAgent
from sam.base.vnf import VNF_TYPE_RATELIMITER, VNFI, VNFIStatus
from sam.serverController.sffController.sibMaintainer import SIBMaintainer


class VNFControllerStub(object):
    def __init__(self):
        logConfigur = LoggerConfigurator(__name__, './log',
            'vnfController.log', level='debug')
        self.logger = logConfigur.getLogger()

        self.mA = MessageAgent()
        self.mA.startMsgReceiverRPCServer(VNF_CONTROLLER_IP, VNF_CONTROLLER_PORT)

        self.sibm = SIBMaintainer()
        self.vnfBase = {}

    def sendCmdRply(self, cmdRply):
        msg = SAMMessage(MSG_TYPE_VNF_CONTROLLER_CMD_REPLY, cmdRply)
        self.mA.sendMsg(MEDIATOR_QUEUE, msg)

    def installVNF(self, sshUsrname, sshPassword, remoteIP, vnfiID, privateKeyFilePath=None):
        self.vnfBase[remoteIP] = {}
        self.vnfBase[remoteIP]["VNFAggCount"] = 0
        command = self.genVNFInstallationCommand(remoteIP, vnfiID)
        self.sshA = SSHAgent()
        if privateKeyFilePath == None:
            self.sshA.connectSSH(sshUsrname, sshPassword, remoteIP, remoteSSHPort=22)
        else:
            self.sshA.connectSSHWithRSA(sshUsrname, privateKeyFilePath, remoteIP)
            self.sshA.passwd = sshPassword
        shellCmdRply = self.sshA.runShellCommandWithSudo(command, 2)
        # shellCmdRply = self.sshA.runShellCommand(command)
        return shellCmdRply

    def genVNFInstallationCommand(self,remoteIP,vnfiID):
        vdevs0 = self.sibm.getVdev(vnfiID,0).split(",")
        vdevs1 = self.sibm.getVdev(vnfiID,1).split(",")
        vdev0 = vdevs0[0]
        path0 = vdevs0[1].split("iface=")[1]
        vdev1 = vdevs1[0]
        path1 = vdevs1[1].split("iface=")[1]
        name = self.genVNFName(remoteIP)
        command = "sudo -S docker run -ti --rm --privileged  --name="+ str(name) + " " \
            + "-v /mnt/huge_1GB:/dev/hugepages " \
            + "-v /tmp/:/tmp/ " \
            + "dpdk-app-testpmd ./build/app/testpmd -l 0-1 -n 1 -m 1024 --no-pci " \
            + "--vdev=net_virtio_user0" + ",path=" + path0 + " " \
            + "--vdev=net_virtio_user1" + ",path=" + path1 + " " \
            + "--file-prefix=virtio --log-level=8 -- " \
            + "--txqflags=0xf00 --disable-hw-vlan --forward-mode=io --port-topology=chained --total-num-mbufs=2048 -a"
        self.vnfBase[remoteIP][vnfiID] = {"name":name}
        logging.info(command)
        return command

    def genVNFName(self,remoteIP):
        self.vnfBase[remoteIP]["VNFAggCount"] = self.vnfBase[remoteIP]["VNFAggCount"] + 1
        return "name"+str(self.vnfBase[remoteIP]["VNFAggCount"])

    def getVNFName(self,remoteIP,vnfiID):
        return self.vnfBase[remoteIP][vnfiID]["name"]

    def uninstallVNF(self,sshUsrname,sshPassword,remoteIP,vnfiID,privateKeyFilePath=None):
        command = self.genVNFUninstallationCommand(remoteIP,vnfiID)
        self.sshA = SSHAgent()
        # self.sshA.connectSSH(sshUsrname, sshPassword, remoteIP, remoteSSHPort=22)
        if privateKeyFilePath == None:
            self.sshA.connectSSH(sshUsrname, sshPassword, remoteIP, remoteSSHPort=22)
        else:
            self.sshA.connectSSHWithRSA(sshUsrname, privateKeyFilePath, remoteIP)
            self.sshA.passwd = sshPassword
        shellCmdRply = self.sshA.runShellCommandWithSudo(command,None)
        # logging.info(
        #     "command reply:\n stdin:{0}\n stdout:{1}\n stderr:{2}".format(
        #     None,
        #     shellCmdRply['stdout'].read().decode('utf-8'),
        #     shellCmdRply['stderr'].read().decode('utf-8')))
        del self.vnfBase[remoteIP][vnfiID]
        return shellCmdRply

    def genVNFUninstallationCommand(self,remoteIP,vnfiID):
        name = self.getVNFName(remoteIP,vnfiID)
        command = "sudo -S docker stop "+name
        logging.info(command)
        return command

    def recvCmdFromMeasurer(self):
        while True:
            msg = self.mA.getMsgByRPC(VNF_CONTROLLER_IP, VNF_CONTROLLER_PORT)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            else:
                body = msg.getbody()
                source = msg.getSource()
                try:
                    if self.mA.isRequest(body):
                        pass
                    elif self.mA.isCommand(body):
                        rplyMsg = self._command_handler(body)
                        self.mA.sendMsgByRPC(source["srcIP"], source["srcPort"], rplyMsg)
                        break
                    else:
                        self.logger.error("Unknown massage body")
                except Exception as ex:
                    ExceptionProcessor(self.logger).logException(ex,
                        "measurer")

    def _command_handler(self, cmd):
        self.logger.debug(" VNFController gets a command ")
        attributes = {}
        try:
            attributes = self.genSFCIAttr()
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, "vnfController")
        finally:
            attributes.update({'source':'vnfController', 'zone':TURBONET_ZONE})
            cmdRply = CommandReply(cmd.cmdID, CMD_STATE_SUCCESSFUL, attributes)
            rplyMsg = SAMMessage(MSG_TYPE_VNF_CONTROLLER_CMD_REPLY, cmdRply)
        return rplyMsg

    def genSFCIAttr(self):
        sfciDict = {}
        vnfiSeq = [
                    [VNFI(VNF_TYPE_RATELIMITER,VNF_TYPE_RATELIMITER,1,1,1,
                            VNFIStatus(state={
                                "vnfType": VNF_TYPE_RATELIMITER,
                                "rateLimitition":1}))
                    ]
                ]
        slo = SLO()
        sfci = SFCI(1,vnfiSequence=vnfiSeq,sloRealTimeValue=slo)
        sfciDict[1] = sfci

        return {'sfcisDict':sfciDict,
                'zone':TURBONET_ZONE
                }
