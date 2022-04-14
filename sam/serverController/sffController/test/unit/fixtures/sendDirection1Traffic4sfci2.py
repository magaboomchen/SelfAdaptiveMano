#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
from scapy.all import *
import logging
import time
from sam.base.socketConverter import SocketConverter, BCAST_MAC
from sam.test.testBase import *
from sam.serverController.sffController.test.unit.test_sffSFCIAdder import *

global VNFI1_1_IP
VNFI1_1_IP = "10.16.2.128"

def sendDirection1Traffic4sfci2():
    data = "Hello World"
    ether = Ether(src=TESTER_SERVER_DATAPATH_MAC, dst=SFF1_DATAPATH_MAC)
    ip1 = IP(src=CLASSIFIER_DATAPATH_IP,dst=VNFI1_1_IP)
    ip2 = IP(src=WEBSITE_REAL_IP,dst=OUTTER_CLIENT_IP)
    tcp = TCP(sport=80,dport=1234)
    frame = ether / ip1 / ip2 / tcp /Raw(load=data)
    sendp(frame,iface="toVNF1")

if __name__=="__main__":
    time.sleep(0.1)
    sendDirection1Traffic4sfci2()