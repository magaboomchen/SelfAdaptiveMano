#!/usr/bin/python
# -*- coding: UTF-8 -*-

from scapy.all import *
import time

from sam.base.socketConverter import *
from sam.test.testBase import *
from sam.serverController.classifierController.test.unit.test_SFCIAdder import *

def sendOutSFCDomainTraffic2Classifier():
    data = "Hello World"
    ether = Ether(src=TESTER_SERVER_DATAPATH_MAC, dst=CLASSIFIER_DATAPATH_MAC)
    ip1 = IP(src=VNFI1_0_IP,dst=SFCI1_0_EGRESS_IP)
    ip2 = IP(src=WEBSITE_REAL_IP,dst=OUTTER_CLIENT_IP)
    tcp = TCP(sport=1234,dport=80)
    frame = ether / ip1 / ip2 / tcp /Raw(load=data)
    sendp(frame,iface="toClassifier")

if __name__=="__main__":
    time.sleep(0.1)
    sendOutSFCDomainTraffic2Classifier()