#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
sudo python sendInboundTraffic.py -i eno2 -sip 2.2.0.36 -dip 2.2.0.33 -smac 18:66:da:86:4c:16 -dmac cc:37:ab:a0:a8:41
'''

import time
import argparse

from scapy.all import Raw, sendp
from scapy.layers.l2 import Ether
from scapy.layers.inet import IP, TCP

from sam.base.argParser import ArgParserBase
from sam.test.testBase import WEBSITE_REAL_IP, OUTTER_CLIENT_IP, \
    TESTER_SERVER_DATAPATH_MAC, CLASSIFIER_DATAPATH_MAC


class ArgParser(ArgParserBase):
    def __init__(self, *args, **kwargs):
        super(ArgParser, self).__init__(*args, **kwargs)
        self.parser = argparse.ArgumentParser(description='send a inbound frame.', add_help=False)
        self.parser.add_argument('-i', metavar='outIntf', type=str, nargs='?', const=1, default='toClassifier',
            help="output interface")
        self.parser.add_argument('-smac', metavar='src mac', type=str, nargs='?', const=1, default=TESTER_SERVER_DATAPATH_MAC,
            help="hw src mac")
        self.parser.add_argument('-dmac', metavar='dst mac', type=str, nargs='?', const=1, default=CLASSIFIER_DATAPATH_MAC,
            help="hw dst mac")
        self.parser.add_argument('-sip', metavar='src ip', type=str, nargs='?', const=1, default=OUTTER_CLIENT_IP,
            help="source ip")
        self.parser.add_argument('-dip', metavar='dst ip', type=str, nargs='?', const=1, default=WEBSITE_REAL_IP,
            help="dest ip")
        self.parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                            help='Example usage: python sendInboundTraffic.py -i enp4s0 ' \
                                '-smac 00:1b:21:c0:8f:ae -dmac 00:1b:21:c0:8f:ae -sip 1.1.1.1 -dip 2.2.0.36')
        self.args = self.parser.parse_args()


def sendInboundTraffic2Classifier(iface, smac, dmac, sip, dip):
    data = "Hello World"
    ether = Ether(src=smac, dst=dmac)
    ip = IP(src=sip,dst=dip)
    tcp = TCP(sport=1234, dport=80)
    frame = ether / ip / tcp /Raw(load=data)
    sendp(frame,iface=iface)


if __name__=="__main__":
    time.sleep(0.1)
    argParser = ArgParser()
    iface = argParser.getArgs()['i']
    smac = argParser.getArgs()['smac']
    dmac = argParser.getArgs()['dmac']
    sip = argParser.getArgs()['sip']
    dip = argParser.getArgs()['dip']

    while True:
        time.sleep(1)
        sendInboundTraffic2Classifier(iface, smac, dmac, sip, dip)