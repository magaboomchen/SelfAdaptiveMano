import logging

from sam.base.messageAgent import *
from sam.base.command import *
from sam.base.sfc import *
from sam.base.vnf import *
from sam.base.shellProcessor import *
from sam.base.sshAgent import *
from sam.serverController.sffController.sibMaintainer import *


class VNFControllerStub(object):
    def __init__(self):
        self.mA = MessageAgent()
        self.sibm = SIBMaintainer()
        self.vnfBase = {}
        # self.mA.startRecvMsg(VNF_CONTROLLER_QUEUE)

    def sendCmdRply(self,cmdRply):
        msg = SAMMessage(MSG_TYPE_VNF_CONTROLLER_CMD_REPLY, cmdRply)
        self.mA.sendMsg(MEDIATOR_QUEUE,msg)

    def installVNF(self,sshUsrname,sshPassword,remoteIP,VNFIID):
        self.vnfBase[remoteIP] = {}
        self.vnfBase[remoteIP]["VNFAggCount"] = 0
        command = self.genVNFInstallationCommand(remoteIP,VNFIID)
        self.sshA = SSHAgent()
        self.sshA.connectSSH(sshUsrname, sshPassword, remoteIP, remoteSSHPort=22)
        shellCmdRply = self.sshA.runShellCommandWithSudo(command,1)
        return shellCmdRply

    def genVNFInstallationCommand(self,remoteIP,VNFIID):
        vdevs0 = self.sibm.getVdev(VNFIID,0).split(",")
        vdevs1 = self.sibm.getVdev(VNFIID,1).split(",")
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
        self.vnfBase[remoteIP][VNFIID] = {"name":name}
        return command

    def genVNFName(self,remoteIP):
        self.vnfBase[remoteIP]["VNFAggCount"] = self.vnfBase[remoteIP]["VNFAggCount"] + 1
        return "name"+str(self.vnfBase[remoteIP]["VNFAggCount"])

    def getVNFName(self,remoteIP,VNFIID):
        return self.vnfBase[remoteIP][VNFIID]["name"]

    def uninstallVNF(self,sshUsrname,sshPassword,remoteIP,VNFIID):
        command = self.genVNFUninstallationCommand(remoteIP,VNFIID)
        self.sshA = SSHAgent()
        self.sshA.connectSSH(sshUsrname, sshPassword, remoteIP, remoteSSHPort=22)
        shellCmdRply = self.sshA.runShellCommandWithSudo(command,None)
        # logging.info(
        #     "command reply:\n stdin:{0}\n stdout:{1}\n stderr:{2}".format(
        #     None,
        #     shellCmdRply['stdout'].read().decode('utf-8'),
        #     shellCmdRply['stderr'].read().decode('utf-8')))
        del self.vnfBase[remoteIP][VNFIID]
        return shellCmdRply

    def genVNFUninstallationCommand(self,remoteIP,VNFIID):
        name = self.getVNFName(remoteIP,VNFIID)
        command = "sudo -S docker stop "+name
        logging.info(command)
        return command