import os
from scapy.all import *
import logging
import time
from sam.base.socketConverter import *
from sam.test.testBase import *
from sam.serverController.vnfController.test.test_vnfControllerAddNAT import *

def sendDirection1Traffic():
    data = "Hello World"
    ether = Ether(src=TESTER_SERVER_DATAPATH_MAC, dst=SFF0_DATAPATH_MAC)
    ip1 = IP(src=CLASSIFIER_DATAPATH_IP,dst=NAT_VNFI1_1_IP)
    #ip2 = IP(src=WEBSITE_REAL_IP,dst=NAT_PIP)
    #tcp = UDP(sport=80,dport=NAT_MIN_PORT)
    ip2 = IP(src='5.0.0.5',dst='8.0.8.8')
    tcp = UDP(sport=4969,dport=11111)
    frame = ether / ip1 / ip2 / tcp /Raw(load=data)
    sendp(frame,iface="ens8")

if __name__=="__main__":
    time.sleep(0.1)
    sendDirection1Traffic()