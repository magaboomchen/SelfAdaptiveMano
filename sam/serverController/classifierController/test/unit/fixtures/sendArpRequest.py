import os
from scapy.all import *
import logging
import time
from sam.base.socketConverter import *
from sam.test.testBase import *

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