# #!/usr/bin/env python
# import pika
# import sys
# import base64
# import pickle
# import time
# import uuid
# import os
# import subprocess
# import logging
# import Queue
# import threading
# import datetime
# import sys
# import ctypes
# import inspect
# import argparse

# from sam.base.server import Server
# from sam.base.messageAgent import *
# from sam.orchestrator import *
# from sam.base.sfc import *
# from sam.serverController.bessController import *
# from sam.base.argParser import *

# class ArgParser(ArgParserBase):
#     def __init__(self, *args, **kwargs):
#         super(ArgParser, self).__init__(*args, **kwargs)
#         parser = argparse.ArgumentParser(description='Set bess controller tester.')
#         parser.add_argument('bessServerIP', metavar='bsi', type=str, 
#             help='ip address of bess server, e.g. 192.168.122.208')
#         self._args = parser.parse_args()

# class BessControllerTester(object):
#     def __init__(self,serverControlNICIP):
#         logging.info('Init BessControllerTester')
#         self._messageAgent = MessageAgent()
#         self._messageAgent.startRecvMsg(ORCHESTRATION_MODULE_QUEUE)
#         self._serverControlNicIP = serverControlNICIP

#     def sendCmdtoBESSController(self, bessCmd):
#         msg = SAMMessage(MSG_TYPE_BESSCMD,bessCmd)
#         self._messageAgent.sendMsg(BESS_CONTROLLER_QUEUE,msg)

#     def genBESSCmd(self, cmdType,cmdID,sfc):
#         bessCmd = BESSCmd(
#             {
#                 "cmdType":cmdType,
#                 "cmdID":cmdID,
#                 "sfc":sfc
#             }
#         )
#         return bessCmd

#     def genSFC(self):
#         vnf1 = self._genVNFFW()
#         vnf2 = self._genVNFNAT()
#         print([[vnf1],[vnf2]])
#         return DeploySFCIinServerCmd(
#             TODO
#         )

#     def _genVNFFW(self):
#         return VNFI(TODO：修改了VNFI的init函数，这里需要重构
#                 {
#                     "VNFID":VNF_TYPE_FW, 
#                     "VNFType":"VNF_TYPE_FW",
#                     "VNFIID": "FW1", #uuid.uuid1(),    # this field is used to name PMDPort
#                     "config":"CONFIG.TXT CONTENT HERE",
#                     "serverControlNICMAC":"52:54:00:80:ea:94",
#                     "serverControlNICIP":self._serverControlNicIP,
#                     "serverDatapathNICIP":["10.1.1.1","10.1.1.2"]
#                 }
#             )

#     def _genVNFNAT(self):
#         return VNFI(TODO：修改了VNFI的init函数，这里需要重构
#                 {
#                     "VNFID":VNF_TYPE_NAT, 
#                     "VNFType":"VNF_TYPE_NAT",
#                     "VNFIID": "NAT1", #uuid.uuid1(),   # this field is used to name PMDPort
#                     "config":"CONFIG.TXT CONTENT HERE",
#                     "serverControlNICMAC":"52:54:00:80:ea:94",
#                     "serverControlNICIP":self._serverControlNicIP,
#                     "serverDatapathNICIP":["10.1.2.1","10.1.2.2"]
#                 }
#             )

# if __name__=="__main__":
#     logging.basicConfig(level=logging.INFO)

#     argParser = ArgParser()
#     serverControlNICIP = argParser.getArgs()['bessServerIP']   # example: 192.168.122.208

#     bessControllerTester = BessControllerTester(serverControlNICIP)
#     sfc = bessControllerTester.genSFC()
#     while True:
#         userCmd = raw_input(
#             "please input user command.\n \
#             add: start add sfc in bess\n \
#             del: to delete sfc on bess\n \
#             Your input is:"
#             )
#         if userCmd == "add":
#             logging.info("start add sfc in bess.")
#             cmdID = uuid.uuid1()
#             bessCmd = bessControllerTester.genBESSCmd(BESS_CMD_TYPE_ADD_SFC,cmdID,sfc)
#             bessControllerTester.sendCmdtoBESSController(bessCmd)
#         elif userCmd == "del":
#             logging.info("start delete sfc in bess.")
#             cmdID = uuid.uuid1()
#             bessCmd = bessControllerTester.genBESSCmd(BESS_CMD_TYPE_DEL_SFC,cmdID,sfc)
#             bessControllerTester.sendCmdtoBESSController(bessCmd)
#         else:
#             logging.warning("Unknown input.")