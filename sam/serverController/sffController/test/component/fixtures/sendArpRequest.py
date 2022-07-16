#!/usr/bin/python
# -*- coding: UTF-8 -*-

import time

from scapy.all import sendp
from scapy.layers.l2 import Ether, ARP

from sam.base.socketConverter import BCAST_MAC
from sam.serverController.sffController.test.component.test_sffSFCIAdder import TESTER_SERVER_DATAPATH_IP, \
    TESTER_SERVER_DATAPATH_MAC,  SFF1_DATAPATH_IP
from sam.test.testBase import TESTER_SERVER_INTF 


def sendArpRequest( outIntf, requestIP):
    arp = ARP(op=1,
            psrc=TESTER_SERVER_DATAPATH_IP,
            pdst=requestIP,
            hwsrc=TESTER_SERVER_DATAPATH_MAC ,
            hwdst = "90:e2:ba:0f:a3:b5"
            )
    frame = Ether(src=TESTER_SERVER_DATAPATH_MAC , dst=BCAST_MAC) / arp
    sendp(frame,iface=outIntf)
    frame.show()

if __name__=="__main__":
    time.sleep(0.5)
    sendArpRequest(TESTER_SERVER_INTF, SFF1_DATAPATH_IP)