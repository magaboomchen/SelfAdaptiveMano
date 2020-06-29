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
from bessController import *


class ArgParser():
    def __init__(self):
        parser = argparse.ArgumentParser(description='Set bess controller tester.')
        parser.add_argument('bessServerIP', metavar='bsi', type=str, 
            help='ip address of bess server, e.g. 192.168.122.208')
        self._args = parser.parse_args()

    def getArgs(self):
        return self._args.__dict__
    
    def printArgs(self):
        logging.info("argparse.args=",self._args,type(self._args))
        d = self._args.__dict__
        for key,value in d.iteritems():
            logging.info('%s = %s'%(key,value))

class BessControllerTester():
    def __init__(self,serverPrimaryIP):
        logging.info('Init BessControllerTester')
        self._messageAgent = MessageAgent()
        self._messageAgent.startRecvMsg(ORCHESTRATION_MODULE_QUEUE)
        self._serverPrimaryIP = serverPrimaryIP

    def sendCmdtoBESSController(self, bessCmd):
        msg = SAMMessage(MSG_TYPE_BESSCMD,bessCmd)
        self._messageAgent.sendMsg(BESS_CONTROLLER_QUEUE,msg)

    def genBESSCmd(self, cmdType,cmdID,sfc):
        bessCmd = BESSCmd(
            {
                "cmdType":cmdType,
                "cmdID":cmdID,
                "sfc":sfc
            }
        )
        return bessCmd

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
                    "VNFUUID": "FW1", #uuid.uuid4(),    # this field is used to name PMDPort
                    "config":"CONFIG.TXT CONTENT HERE",
                    "serverMAC":"52:54:00:80:ea:94",
                    "serverPrimaryIP":self._serverPrimaryIP,
                    "serverIP":["10.1.1.1","10.1.1.2"]
                }
            )

    def _genVNFNAT(self):
        return VNF(
                {
                    "VNFID":VNF_TYPE_NAT, 
                    "VNFType":"VNF_TYPE_NAT",
                    "VNFUUID": "NAT1", #uuid.uuid4(),   # this field is used to name PMDPort
                    "config":"CONFIG.TXT CONTENT HERE",
                    "serverMAC":"52:54:00:80:ea:94",
                    "serverPrimaryIP":self._serverPrimaryIP,
                    "serverIP":["10.1.2.1","10.1.2.2"]
                }
            )

if __name__=="__main__":
    logging.basicConfig(level=logging.INFO)

    argParser = ArgParser()
    serverPrimaryIP = argParser.getArgs()['bessServerIP']   # example: 192.168.122.208

    bessControllerTester = BessControllerTester(serverPrimaryIP)
    sfc = bessControllerTester.genSFC()
    while True:
        userCmd = raw_input(
            "please input user command.\n \
            add: start add sfc in bess\n \
            del: to delete sfc on bess\n \
            Your input is:"
            )
        if userCmd == "add":
            logging.info("start add sfc in bess.")
            cmdID = uuid.uuid4()
            bessCmd = bessControllerTester.genBESSCmd(BESS_CMD_TYPE_ADD_SFC,cmdID,sfc)
            bessControllerTester.sendCmdtoBESSController(bessCmd)
        elif userCmd == "del":
            logging.info("start delete sfc in bess.")
            cmdID = uuid.uuid4()
            bessCmd = bessControllerTester.genBESSCmd(BESS_CMD_TYPE_DEL_SFC,cmdID,sfc)
            bessControllerTester.sendCmdtoBESSController(bessCmd)
        else:
            logging.warning("Unknown input.")