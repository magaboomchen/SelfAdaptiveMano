from sam.base.messageAgent import *
from sam.base.command import *
from sam.base.sfc import *
from sam.base.vnf import *
from sam.base.shellProcessor import *
from sam.base.sshProcessor import *
from sam.serverController.sffController.sibMaintainer import *

class VNFControllerStub(object):
    def __init__(self):
        self.mA = MessageAgent()
        self.sibm = SIBMaintainer()
        # self.mA.startRecvMsg(VNF_CONTROLLER_QUEUE)

    def sendCmdRply(self,cmdRply):
        msg = SAMMessage(MSG_TYPE_VNF_CONTROLLER_CMD_REPLY, cmdRply)
        self.mA.sendMsg(MEDIATOR_QUEUE,msg)

    def installVNF(self,sshUsrname,sshPassword,remoteIP,VNFIID,directions):
        command = self.genVNFInstallationCommand(VNFIID,directions)
        print(command)
        # self.rS = SSHProcessor()
        # self.rS.connectSSH(sshUsrname, sshPassword, remoteIP, remoteSSHPort=22)
        # self.rS.runShellCommand(command)

    def genVNFInstallationCommand(self,VNFIID,directions):
        vdevs0 = self.sibm.getVdev(VNFIID,directions[0]["ID"]).split(",")
        vdevs1 = self.sibm.getVdev(VNFIID,directions[1]["ID"]).split(",")
        vdev0 = vdevs0[0]
        path0 = vdevs0[1].split("iface=")[1]
        vdev1 = vdevs1[0]
        path1 = vdevs1[1].split("iface=")[1]
        # "--vdev=" + vdev0 + ",path=" + path0 + " " + \
        # "--vdev=" + vdev1 + ",path=" + path1 + " " + \
        command = "sudo docker run -ti --rm --privileged  --name=test " + \
            "-v /mnt/huge_1GB:/dev/hugepages " + \
            "-v /tmp/:/tmp/ " + \
            "dpdk-app-testpmd ./x86_64-native-linuxapp-gcc/app/testpmd -l 0-1 -n 1 -m 1024 --no-pci " + \
            "-l 1-2 -n 1 -m 1024 --no-pci " + \
            "--vdev=net_virtio_user0" + ",path=" + path0 + " " + \
            "--vdev=net_virtio_user1" + ",path=" + path1 + " " + \
            "--file-prefix=virtio --log-level=8 -- " + \
            "--txqflags=0xf00 --disable-hw-vlan --forward-mode=io --port-topology=chained --total-num-mbufs=2048 -a"
        return command