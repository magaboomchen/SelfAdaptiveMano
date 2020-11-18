import os
from scapy.all import *
import logging
import time
from sam.base.socketConverter import *
from sam.test.testBase import *
from sam.serverController.vnfController.test.test_vnfControllerAddNAT import *

def sendDirection0Traffic():
    data = "Hello World"
    ether = Ether(src=TESTER_SERVER_DATAPATH_MAC, dst=SFF0_DATAPATH_MAC)
    ip1 = IP(src=CLASSIFIER_DATAPATH_IP,dst=NAT_VNFI1_0_IP)
    #ip2 = IP(src=OUTTER_CLIENT_IP,dst=WEBSITE_REAL_IP)
    #tcp = UDP(sport=1234,dport=80)
    ip2 = IP(src='3.0.0.4',dst='5.0.0.5')
    tcp = UDP(sport=4969,dport=4969)
    frame = ether / ip1 / ip2 / tcp /Raw(load=data)
    sendp(frame,iface="ens8")

if __name__=="__main__":
    time.sleep(0.1)
    sendDirection0Traffic()