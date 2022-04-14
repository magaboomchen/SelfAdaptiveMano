#!/usr/bin/python
# -*- coding: UTF-8 -*-

import time

from scapy.all import Raw, sendp
from scapy.layers.l2 import Ether
from scapy.layers.inet import IP, TCP

from sam.test.testBase import VNFI1_0_IP, SFF1_DATAPATH_MAC, WEBSITE_REAL_IP, \
    TESTER_SERVER_DATAPATH_MAC, CLASSIFIER_DATAPATH_IP, OUTTER_CLIENT_IP


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