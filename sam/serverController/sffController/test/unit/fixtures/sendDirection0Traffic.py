#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
from scapy.all import *
import logging
import time
from sam.base.socketConverter import SocketConverter, BCAST_MAC
from sam.test.testBase import *
# from sam.serverController.sffController.test.unit.test_sffSFCIAdder import *


def sendDirection0Traffic():
    data = "Hello World"
    ether = Ether(src=TESTER_SERVER_DATAPATH_MAC, dst=SFF1_DATAPATH_MAC)
    ip1 = IP(src=CLASSIFIER_DATAPATH_IP,dst=VNFI1_0_IP)
    ip2 = IP(src=OUTTER_CLIENT_IP,dst=WEBSITE_REAL_IP)
    tcp = TCP(sport=1234,dport=80)
    frame = ether / ip1 / ip2 / tcp /Raw(load=data)
    sendp(frame,iface="toVNF1")

if __name__=="__main__":
    time.sleep(0.1)
    sendDirection0Traffic()