#!/usr/bin/python
# -*- coding: UTF-8 -*-

import time
import argparse

from scapy.all import sendp
from scapy.layers.l2 import Ether, ARP

from sam.base.argParser import ArgParserBase
from sam.base.socketConverter import BCAST_MAC


class ArgParser(ArgParserBase):
    def __init__(self, *args, **kwargs):
        super(ArgParser, self).__init__(*args, **kwargs)
        self.parser = argparse.ArgumentParser(description='send Arp frame.', add_help=False)
        self.parser.add_argument('-i', metavar='outIntf', type=str, nargs='?', const=1, default='toClassifier',
            help="output interface")
        self.parser.add_argument('-sip', metavar='psrc', type=str, nargs='?', const=1, default="192.168.123.1",
            help="arp source ip")
        self.parser.add_argument('-dip', metavar='requestIP', type=str, nargs='?', const=1, default="0.0.0.0",
            help="request dest IP")
        self.parser.add_argument('-smac', metavar='hwsrc', type=str, nargs='?', const=1, default="fe:54:00:05:4d:7d",
            help="hw src mac")
        self.parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                            help='Example usage: python sendArpRequest.py -o enp4s0 -sip 1.1.1.1 -dip 2.2.0.36 -smac 00:1b:21:c0:8f:ae')
        self.args = self.parser.parse_args()


def sendArpRequest(outIntf, psrc, requestIP, hwsrc):
    arp = ARP(op=1, psrc=psrc, pdst=requestIP, hwsrc=hwsrc)
    frame = Ether(src=hwsrc , dst=BCAST_MAC) / arp
    sendp(frame,iface=outIntf)
    print("send arp frame")
    frame.show()


if __name__=="__main__":
    time.sleep(1)
    argParser = ArgParser()
    outIntf = argParser.getArgs()['i']
    psrc = argParser.getArgs()['sip']
    requestIP = argParser.getArgs()['dip']
    hwsrc = argParser.getArgs()['smac']
    sendArpRequest(outIntf=outIntf, psrc=psrc,
        requestIP=requestIP, hwsrc=hwsrc)