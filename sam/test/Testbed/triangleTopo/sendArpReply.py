#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
sudo python sendArpReply.py -i eth0 -sip 1.1.1.2 -dip 2.2.0.33 -smac 18:66:da:85:f9:ed -dmac cc:37:ab:a0:a8:41
'''

import time
import argparse

from scapy.all import sendp
from scapy.layers.l2 import Ether, ARP

from sam.base.argParser import ArgParserBase


class ArgParser(ArgParserBase):
    def __init__(self, *args, **kwargs):
        super(ArgParser, self).__init__(*args, **kwargs)
        self.parser = argparse.ArgumentParser(description='send Arp frame.', add_help=False)
        self.parser.add_argument('-i', metavar='outIntf', type=str, nargs='?', const=1, default='toClassifier',
            help="output interface")
        self.parser.add_argument('-sip', metavar='psrc', type=str, nargs='?', const=1, default="192.168.123.1",
            help="arp source ip")
        self.parser.add_argument('-dip', metavar='replyIP', type=str, nargs='?', const=1, default="0.0.0.0",
            help="reply dest IP")
        self.parser.add_argument('-smac', metavar='hwsrc', type=str, nargs='?', const=1, default="fe:54:00:05:4d:7d",
            help="hw src mac")
        self.parser.add_argument('-dmac', metavar='hwdst', type=str, nargs='?', const=1, default="fe:54:00:05:4d:7d",
            help="hw dst mac")
        self.parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                            help='Example usage: python sendArpReply.py -i eno2 -sip 2.2.0.36 -dip 2.2.0.33 -smac 18:66:da:86:4c:16 -dmac cc:37:ab:a0:a8:41')
        self.args = self.parser.parse_args()


def sendArpReply(outIntf, psrc, replyIP, hwsrc, hwdst):
    arp = ARP(op=2, psrc=psrc, pdst=replyIP, hwsrc=hwsrc)
    frame = Ether(src=hwsrc , dst=hwdst) / arp
    sendp(frame, iface=outIntf)
    print("send arp  reply frame")
    frame.show()


if __name__=="__main__":
    argParser = ArgParser()
    outIntf = argParser.getArgs()['i']
    psrc = argParser.getArgs()['sip']
    replyIP = argParser.getArgs()['dip']
    hwsrc = argParser.getArgs()['smac']
    hwdst = argParser.getArgs()['dmac']
    while True:
        time.sleep(1)
        sendArpReply(outIntf=outIntf, psrc=psrc,
            replyIP=replyIP, hwsrc=hwsrc, hwdst=hwdst)

