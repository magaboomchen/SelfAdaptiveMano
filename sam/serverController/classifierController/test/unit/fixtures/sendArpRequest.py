import os
from scapy.all import *
import logging
import time
from sam.base.socketConverter import *

def sendArpRequest( outIntf, requestIP):
    arp = ARP(op=1,
            psrc="2.2.123.1",
            pdst=requestIP,
            hwsrc="fe:54:00:05:4d:7d"
            )
    frame = Ether(src="fe:54:00:05:4d:7d", dst=BCAST_MAC) / arp
    sendp(frame,iface=outIntf)

if __name__=="__main__":
    time.sleep(1)
    sendArpRequest("toClassifier","2.2.0.35")