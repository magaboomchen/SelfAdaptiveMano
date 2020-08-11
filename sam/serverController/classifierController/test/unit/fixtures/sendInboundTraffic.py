import os
from scapy.all import *
import logging
import time
from sam.base.socketConverter import *
from sam.test.testBase import *

def sendInboundTraffic2Classifier():
    data = "Hello World"
    ether = Ether(src=TESTER_SERVER_DATAPATH_MAC, dst=CLASSIFIER_DATAPATH_MAC)
    ip = IP(src=OUTTER_CLIENT_IP,dst=WEBSITE_REAL_IP)
    tcp = TCP(sport=1234,dport=80)
    frame = ether / ip / tcp /Raw(load=data)
    sendp(frame,iface="toClassifier")

if __name__=="__main__":
    time.sleep(0.1)
    sendInboundTraffic2Classifier()