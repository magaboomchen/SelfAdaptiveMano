#!/usr/bin/env python
import pika
import sys
import base64
import pickle
import time
import uuid
import os
import subprocess
import logging
import Queue
import threading
import datetime
import sys
import ctypes
import inspect
import argparse
sys.path.append("../../ServerAgent")
from server import Server
sys.path.append("../../Message")
from messageAgent import *
sys.path.append("../../Orchestration")
from orchestrator import *
from vnf import *
from sfc import *
sys.path.append("../")
from dockerController import *

class ArgParser():
    def __init__(self):
        parser = argparse.ArgumentParser(description='Set docker controller tester.')
        parser.add_argument('dockerServerIP', metavar='bsi', type=str, 
            help='ip address of docker server, e.g. 192.168.122.208')
        self._args = parser.parse_args()

    def getArgs(self):
        return self._args.__dict__
    
    def printArgs(self):
        logging.info("argparse.args=",self._args,type(self._args))
        d = self._args.__dict__
        for key,value in d.iteritems():
            logging.info('%s = %s'%(key,value))

class DockerControllerTester():
    def __init__(self,serverPrimaryIP):
        logging.info('Init DockerControllerTester')
        self._messageAgent = MessageAgent()
        self._messageAgent.startRecvMsg(ORCHESTRATION_MODULE_QUEUE)
        self._serverPrimaryIP = serverPrimaryIP

    def sendCmdtoDockerController(self,dockerCmd):
        msg = SAMMessage(MSG_TYPE_DOCKERCMD,dockerCmd)
        self._messageAgent.sendMsg(DOCKER_CONTROLLER_QUEUE,msg)

    def genDockerCmd(self, cmdType,cmdID,sfc):
        dockerCmd = DockerCmd(
            {
                "cmdType":cmdType,
                "cmdID":cmdID,
                "sfc":sfc
            }
        )
        return dockerCmd

    def genSFC(self):
        vnf1 = self._genVNFFW()
        vnf2 = self._genVNFNAT()
        print([[vnf1],[vnf2]])
        return SFC(
            {
                "SFCID":1,
                "VNFISeq":[[vnf1],[vnf2]]
            }
        )

    def _genVNFFW(self):
        return VNF(
                {
                    "VNFID":VNF_TYPE_FW, 
                    "VNFType":"VNF_TYPE_FW",
                    "VNFUUID": "FW1", #uuid.uuid4(),  # this field is used to name vdev. Please see bessController.py BESSController._getVdevOfVNFOutputPMDPort() and _getVdevOfVNFInputPMDPort()
                    "config":"CONFIG.TXT CONTENT HERE",
                    "serverMAC":"52:54:00:80:ea:94",
                    "serverPrimaryIP":self._serverPrimaryIP,    # this is the ip address of a virtual machine, user: t1, passwd: 123
                    "serverIP":["10.1.1.1","10.1.1.2"]
                }
            )

    def _genVNFNAT(self):
        return VNF(
                {
                    "VNFID":VNF_TYPE_NAT, 
                    "VNFType":"VNF_TYPE_NAT",
                    "VNFUUID": "NAT1", #uuid.uuid4(),   # this field is used to name vdev Please see bessController.py BESSController._getVdevOfVNFOutputPMDPort() and _getVdevOfVNFInputPMDPort()
                    "config":"CONFIG.TXT CONTENT HERE",
                    "serverMAC":"52:54:00:80:ea:94",
                    "serverPrimaryIP":self._serverPrimaryIP,    # this is the ip address of a virtual machine, user: t1, passwd: 123
                    "serverIP":["10.1.2.1","10.1.2.2"]
                }
            )

if __name__=="__main__":
    logging.basicConfig(level=logging.INFO)

    argParser = ArgParser()
    serverPrimaryIP = argParser.getArgs()['dockerServerIP']   # example: 192.168.122.208

    dockerControllerTester = DockerControllerTester(serverPrimaryIP)
    sfc = dockerControllerTester.genSFC()
    while True:
        userCmd = raw_input(
            "please input user command.\n \
            add: start add sfc in docker\n \
            del: to delete sfc on docker\n \
            Your input is:"
            )
        if userCmd == "add":
            logging.info("start add sfc in docker.")
            cmdID = uuid.uuid4()
            dockerCmd = dockerControllerTester.genDockerCmd(DOCKER_CMD_TYPE_ADD_SFC,cmdID,sfc)
            dockerControllerTester.sendCmdtoDockerController(dockerCmd)
        elif userCmd == "del":
            logging.info("start delete sfc in docker.")
            cmdID = uuid.uuid4()
            dockerCmd = dockerControllerTester.genDockerCmd(DOCKER_CMD_TYPE_DEL_SFC,cmdID,sfc)
            dockerControllerTester.sendCmdtoDockerController(dockerCmd)
        else:
            logging.warning("Unknown input.")