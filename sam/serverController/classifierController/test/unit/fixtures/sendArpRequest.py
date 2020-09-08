#!/usr/bin/python
# -*- coding: UTF-8 -*-

from scapy.all import *
import time

from sam.base.socketConverter import *
from sam.test.testBase import *
from sam.serverController.classifierController.test.unit.test_SFCIAdder import *

def sendArpRequest( outIntf, requestIP):
    arp = ARP(op=1,
            psrc=TESTER_SERVER_DATAPATH_IP,
            pdst=requestIP,
            hwsrc=TESTER_SERVER_DATAPATH_MAC 
            )
    frame = Ether(src=TESTER_SERVER_DATAPATH_MAC , dst=BCAST_MAC) / arp
    sendp(frame,iface=outIntf)

if __name__=="__main__":
    time.sleep(0.1)
    sendArpRequest("toClassifier",CLASSIFIER_DATAPATH_IP)