#!/usr/bin/python
# -*- coding: UTF-8 -*-

import time

from scapy.all import sendp
from scapy.layers.l2 import Ether, ARP

from sam.base.socketConverter import BCAST_MAC
from sam.serverController.sffController.test.unit.test_sffSFCIAdder import TESTER_SERVER_DATAPATH_IP, \
    TESTER_SERVER_DATAPATH_MAC,  SFF1_DATAPATH_IP 


def sendArpRequest( outIntf, requestIP):
    arp = ARP(op=1,
            psrc=TESTER_SERVER_DATAPATH_IP,
            pdst=requestIP,
            hwsrc=TESTER_SERVER_DATAPATH_MAC 
            )
    frame = Ether(src=TESTER_SERVER_DATAPATH_MAC , dst=BCAST_MAC) / arp
    sendp(frame,iface=outIntf)

if __name__=="__main__":
    time.sleep(0.5)
    sendArpRequest("toVNF1", SFF1_DATAPATH_IP)