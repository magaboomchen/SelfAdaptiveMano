#!/usr/bin/python
# -*- coding: UTF-8 -*-

import time
import argparse

from scapy.all import Raw, sendp, sniff
from scapy.layers.l2 import Ether, ARP
from scapy.layers.inet import IP, TCP

from sam.base.argParser import ArgParserBase
from sam.test.testBase import TESTER_SERVER_DATAPATH_MAC, CLASSIFIER_DATAPATH_IP, \
    WEBSITE_REAL_IP, OUTTER_CLIENT_IP, VNFI1_0_IP


class ArgParser(ArgParserBase):
    def __init__(self, *args, **kwargs):
        super(ArgParser, self).__init__(*args, **kwargs)
        self.parser = argparse.ArgumentParser(description='send a sfc frame.', add_help=False)
        self.parser.add_argument('-i', metavar='outIntf', type=str, nargs='?', const=1, default="ens8",
            help="output interface")
        self.parser.add_argument('-smac', metavar='src mac', type=str, nargs='?', const=1, default=TESTER_SERVER_DATAPATH_MAC,
            help="hw src mac")
        self.parser.add_argument('-dmac', metavar='dst mac', type=str, nargs='?', const=1, default=TESTER_SERVER_DATAPATH_MAC,
            help="hw dst mac")
        self.parser.add_argument('-osip', metavar='outter src ip', type=str, nargs='?', const=1, default=CLASSIFIER_DATAPATH_IP,
            help="outter source ip")
        self.parser.add_argument('-odip', metavar='outter dst ip', type=str, nargs='?', const=1, default=VNFI1_0_IP,
            help="outter dest ip")
        self.parser.add_argument('-isip', metavar='inner src ip', type=str, nargs='?', const=1, default=OUTTER_CLIENT_IP,
            help="inner source ip")
        self.parser.add_argument('-idip', metavar='inner dst ip', type=str, nargs='?', const=1, default=WEBSITE_REAL_IP,
            help="inner dest ip")
        self.parser.add_argument('-pl', metavar='payload', type=str, nargs='?', const=1, default="Hello World",
            help="payload")
        self.parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                            help='Example usage: python sendSFCTraffic.py -i ens8 ' \
                                '-smac 00:1b:21:c0:8f:ae -dmac 00:1b:21:c0:8f:ae ' \
                                '-osip 2.2.0.36 -odip 10.16.1.1 -isip 1.1.1.1 -idip 2.2.0.34')
        self.args = self.parser.parse_args()


def sendSFCTraffic(iface, smac, dmac, osip, odip, isip, idip, payLoad):
    data = payLoad
    ether = Ether(src=smac, dst=dmac)
    ip1 = IP(src=osip,dst=odip)
    ip2 = IP(src=isip,dst=idip)
    tcp = TCP(sport=1234,dport=80)
    frame = ether / ip1 / ip2 / tcp /Raw(load=data)
    sendp(frame,iface=iface)


if __name__=="__main__":
    time.sleep(0.1)
    argParser = ArgParser()
    iface = argParser.getArgs()['i']
    smac = argParser.getArgs()['smac']
    dmac = argParser.getArgs()['dmac']
    osip = argParser.getArgs()['osip']
    odip = argParser.getArgs()['odip']
    isip = argParser.getArgs()['isip']
    idip = argParser.getArgs()['idip']
    payLoad = argParser.getArgs()['pl']
    sendSFCTraffic(iface, smac, dmac, osip, odip, isip, idip, payLoad)