import os
from scapy.all import *
import logging
from sam.base.socketConverter import *

def sendFrame2Classifier():
    frame = Ether(src=TESTER_SERVER_DATAPATH_MAC , dst=CLASSIFIER_DATAPATH_MAC)
    sendp(frame,iface="toClassifier")

if __name__=="__main__":
    sendFrame2Classifier()