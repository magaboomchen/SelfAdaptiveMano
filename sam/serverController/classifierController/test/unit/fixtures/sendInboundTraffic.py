import os
from scapy.all import *
import logging
import time
from sam.base.socketConverter import *

def sendInboundTraffic2Classifier():
    data = "Hello World"
    ether = Ether(src="fe:54:11:05:4d:7d", dst="52:54:22:05:4D:7D")
    ip = IP(src="1.1.1.1",dst="2.2.2.2")
    tcp = TCP(sport=1234,dport=80)
    frame = ether / ip / tcp /Raw(load=data)
    sendp(frame,iface="toClassifier")

if __name__=="__main__":
    time.sleep(1)
    sendInboundTraffic2Classifier()