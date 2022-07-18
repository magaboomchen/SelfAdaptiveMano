#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
Usage:
    sudo env "PATH=$PATH"  python ./sendFWDirection0Traffic.py 
'''

import time

from scapy.all import Raw, sendp, sniff
from scapy.layers.l2 import Ether, ARP
from scapy.layers.inet import IP, TCP
from scapy.layers.inet6 import IPv6
from scapy.contrib.nsh import NSH
from scapy.contrib.roce import GRH

from sam.base.routingMorphic import IPV4_ROUTE_PROTOCOL, IPV6_ROUTE_PROTOCOL, ROCEV1_ROUTE_PROTOCOL, SRV6_ROUTE_PROTOCOL
from sam.test.testBase import CLASSIFIER_DATAPATH_IP, \
    FW_VNFI1_0_IP, OUTTER_CLIENT_IPV6, WEBSITE_REAL_IP, OUTTER_CLIENT_IP, SFF1_DATAPATH_MAC, \
    DIRECTION0_TRAFFIC_SPI, DIRECTION0_TRAFFIC_SI, WEBSITE_REAL_IPV6
from sam.serverController.sffController.test.component.testConfig import TESTER_DATAPATH_INTF, \
    TESTER_SERVER_DATAPATH_MAC
from sam.serverController.sffController.sfcConfig import CHAIN_TYPE_NSHOVERETH, CHAIN_TYPE_UFRR, DEFAULT_CHAIN_TYPE

SGID = 1234<<64
DGID = 5678<<64

def sendDirection0Traffic(routeMorphic=IPV4_ROUTE_PROTOCOL):
    data = "Hello World"
    ether = Ether(src=TESTER_SERVER_DATAPATH_MAC, dst=SFF1_DATAPATH_MAC)
    if routeMorphic==IPV4_ROUTE_PROTOCOL:
        ip2 = IP(src=OUTTER_CLIENT_IP, dst=WEBSITE_REAL_IP)
    elif routeMorphic in [IPV6_ROUTE_PROTOCOL, SRV6_ROUTE_PROTOCOL]:
        ip2 = IPv6(src=OUTTER_CLIENT_IPV6, dst=WEBSITE_REAL_IPV6)
    elif routeMorphic == ROCEV1_ROUTE_PROTOCOL:
        ip2 = GRH(sgid=SGID, dgid=DGID)
    else:
        pass
    tcp = TCP(sport=1234, dport=80)
    oriPkt = ip2 / tcp / Raw(load=data)
    if DEFAULT_CHAIN_TYPE == CHAIN_TYPE_UFRR:
        ip1 = IP(src=CLASSIFIER_DATAPATH_IP, dst=FW_VNFI1_0_IP)
        frame = ether / ip1 / oriPkt
    elif DEFAULT_CHAIN_TYPE == CHAIN_TYPE_NSHOVERETH:
        if routeMorphic==IPV4_ROUTE_PROTOCOL:
            nextproto=0x1
        elif routeMorphic==IPV6_ROUTE_PROTOCOL:
            nextproto=0x2
        elif routeMorphic==SRV6_ROUTE_PROTOCOL:
            nextproto=0x2
        elif routeMorphic==ROCEV1_ROUTE_PROTOCOL:
            nextproto=0x6
        else:
            pass
        nsh = NSH(spi = DIRECTION0_TRAFFIC_SPI, si = DIRECTION0_TRAFFIC_SI, nextproto=nextproto, length=0x6)
        frame = ether / nsh / oriPkt
    sendp(frame,iface=TESTER_DATAPATH_INTF)
    frame.show()

if __name__=="__main__":
    time.sleep(0.1)
    sendDirection0Traffic()