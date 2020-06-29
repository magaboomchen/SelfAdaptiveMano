#!/usr/bin/env python
import socket
import pika
import base64
import pickle
import time
import uuid
import logging
import Queue
import threading
import sys
sys.path.append("../ServerAgent")
from server import Server
sys.path.append("../Message")
from messageAgent import *
sys.path.append("../Orchestration")
from orchestrator import *
from sfc import *
from vnf import *

"""
大部分软件已经安装。
开发前请阅读此部分。
我们要开发dockerController，它的功能是根据dockerControllerTester()发出的dockerCMD，在指定的server上安装VNF/删除VNF。
PS：VNF跑在docker中。每个VNF都是DPDK开发的，有两个端口。每个端口都和BESS分配的端口（其实就是在/tmp文件夹下紫色的文件vsock_XXX）连接。
PS：从现在开始，虚拟机192.168.122.208分配出来用于开发dockerController。

我们首先来看一下人工如何部署VNF。
部署VNF的前提条件是bess配置了VNF的输入和输出端口：
1）先启动bessController：
python bessController.py
配置bess：
python bessControllerTester() 192.168.122.208
    输入 add 来配置bess
    输入 del 来删除配置
    ctrl-c 退出

下面是人工实现部署docker VNF的过程：
2）在虚拟机（192.168.122.208）中启动docker运行L2forwarding DPDK app的命令：
2.1）启动docker：
docker启动命令
sudo docker run -ti --rm --privileged  --name=test \
-v /mnt/huge_1GB:/dev/hugepages \
-v /tmp/:/tmp/  \
 dpdk-app-testpmd

2.2）在docker中运行testpmd：（注意这里的path=/tmp/vsock和path=/tmp/vsock2要改成DockerCmd中给出的vdev，需要基于dockerController.py的DOCKERController._getVdevOfVNFOutputPMDPort()方法和_getVdevOfVNFInputPMDPort()方法生成）
./x86_64-native-linuxapp-gcc/app/testpmd -m 1024 --no-pci \
 --vdev=net_virtio_user0,path=/tmp/vsock0_FW1 \
--vdev=net_virtio_user1,path=/tmp/vsock1_FW1 \
--file-prefix=virtio --log-level=8 -- \
 --txqflags=0xf00 --disable-hw-vlan --forward-mode=io --port-topology=chained --total-num-mbufs=2048 -a

我们要用程序替代人工，所以要开发这个dockerController
dockerController基于dockerapi开发： https://docker-py.readthedocs.io/en/stable/
需要写代码的地方已经用logging.error("TODO. Text your code here.")标识出来了。
可以先阅读前面的代码理解
"""

DOCKER_CMD_TYPE_ADD_SFC = "DOCKER_CMD_TYPE_ADD_SFC"
DOCKER_CMD_TYPE_DEL_SFC = "DOCKER_CMD_TYPE_DEL_SFC"
DOCKER_CMD_STATE_PROCESSING = "DOCKER_CMD_STATE_PROCESSING"
DOCKER_CMD_STATE_SUCCESSFUL = "DOCKER_CMD_STATE_SUCCESSFUL"
DOCKER_CMD_STATE_FAIL = "DOCKER_CMD_STATE_FAIL"

class DockerCmd():
    def __init__(self, attrDict):
        self.cmdType = attrDict["cmdType"]
        self.cmdID = attrDict["cmdID"]
        self.sfc = attrDict["sfc"]

class DockerController():
    def __init__(self):
        self._serverSet = {}    # store docker server = {"server controll nic (primary) ip": {"Mac":,"DockerState":}}
        self._dockerCmd = {}   # store all docker cmd
        self._messageAgent = MessageAgent()
        self._messageAgent.startRecvMsg(DOCKER_CONTROLLER_QUEUE)

    def startDockerController(self):
        while True:
            msg = self._messageAgent.getMsg(DOCKER_CONTROLLER_QUEUE)
            if msg.getMessageType() == MSG_TYPE_DOCKERCMD:
                logging.info("Docker controller get a docker cmd.")
                try:
                    dockerCmd = msg.getbody()
                    self._dockerCmd[dockerCmd.cmdID] = {"dockerCmd":dockerCmd,"state":DOCKER_CMD_STATE_PROCESSING}
                    # process docker cmd
                    if dockerCmd.cmdType == DOCKER_CMD_TYPE_ADD_SFC:
logging.error("TODO. Text your code here.")
exit(1)
                    elif dockerCmd.cmdType == DOCKER_CMD_TYPE_DEL_SFC:
logging.error("TODO. Text your code here.")
exit(1)
                    else:
                        logging.error("Unkonwn docker cmd type.")
                    # check docker cmd state
                    self._dockerCmd[dockerCmd.cmdID]["state"] = DOCKER_CMD_STATE_SUCCESSFUL
                except ValueError as err:
                    logging.error('docker cmd processing error: ' + repr(err))
                    self._dockerCmd[dockerCmd.cmdID]["state"] = DOCKER_CMD_STATE_FAIL
                finally:
                    # reply the docker cmd
                    rplyMsg = SAMMessage(MSG_TYPE_DOCKERCMD_REPLY, DOCKERCmdReply({"cmdID":dockerCmd.cmdID,"cmdResult":self._dockerCmd[dockerCmd.cmdID]["state"]}) )
                    self._messageAgent.sendMsg(ORCHESTRATION_MODULE_QUEUE,rplyMsg)
            elif msg.getMessageType() == None:
                pass
            else:
                logging.error("Unknown msg type.")

if __name__=="__main__":
    logging.basicConfig(level=logging.INFO)
    dockerController = DockerController()
    dockerController.startDockerController()