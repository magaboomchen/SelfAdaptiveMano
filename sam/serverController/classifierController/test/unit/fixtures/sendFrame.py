#!/usr/bin/python
# -*- coding: UTF-8 -*-

from scapy.all import sendp
from scapy.layers.l2 import Ether

from sam.test.testBase import TESTER_SERVER_DATAPATH_MAC, CLASSIFIER_DATAPATH_MAC


def sendFrame2Classifier():
    frame = Ether(src=TESTER_SERVER_DATAPATH_MAC, dst=CLASSIFIER_DATAPATH_MAC)
    sendp(frame,iface="toClassifier")


if __name__=="__main__":
    sendFrame2Classifier()