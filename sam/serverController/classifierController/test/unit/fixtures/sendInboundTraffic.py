#!/usr/bin/python
# -*- coding: UTF-8 -*-

import time

from scapy.all import *

from sam.base.argParser import *
from sam.base.socketConverter import SocketConverter, BCAST_MAC
from sam.test.testBase import *


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
    tcp = TCP(sport=1234,dport=80)
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
    sendInboundTraffic2Classifier(iface, smac, dmac, sip, dip)