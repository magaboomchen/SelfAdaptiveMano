import os
from scapy.all import *
import logging
from sam.base.socketConverter import *

def sendFrame2Classifier():
    frame = Ether(src="fe:54:11:05:4d:7d", dst="52:54:22:05:4D:7D")
    sendp(frame,iface="toClassifier")

if __name__=="__main__":
    sendFrame2Classifier()