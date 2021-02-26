#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
sudo python ./triangleInBoundTrafficSendRecv.py -i eth0 -sip 1.1.1.2 -dip 3.3.3.3
'''

import time

from scapy.all import *

from sam.base.argParser import *
from sam.base.socketConverter import *


TESTER_SERVER_DATAPATH_MAC = "18:66:da:85:f9:ed"
CLASSIFIER_DATAPATH_MAC = "00:1b:21:c0:8f:ae"
OUTTER_CLIENT_IP = "1.1.1.1"
WEBSITE_REAL_IP = "3.3.3.3"


class ArgParser(ArgParserBase):
    def __init__(self, *args, **kwargs):
        super(ArgParser, self).__init__(*args, **kwargs)
        self.parser = argparse.ArgumentParser(description='send a inbound frame.', add_help=False)
        self.parser.add_argument('-i', metavar='outIntf', type=str, nargs='?', const=1, default='h1-eth0',
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


class TriangleInBoundTrafficSendRecv(object):
    def __init__(self, iface, dmac, sip, dip):
        self._initialTryNum = 3
        self._interval = 1
        self.iface = iface
        self.dmac = dmac
        self.sip = sip
        self.dip = dip

    def start(self):
        self._init()
        self._sendRecv()

    def _init(self):
        for tryNum in range(self._initialTryNum):
            self.sendInboundTraffic2Classifier(self.iface,
                self.sip, self.dip)

    def _sendRecv(self):
        # formal send
        t = self.recvTraffic(self.iface, self.dmac, self.sip, self.dip)
        t.start()
        count = 0
        try:
            while True:
                print("send {0}-th pkt".format(count))
                count = count + 1
                self.sendInboundTraffic2Classifier(self.iface,
                    self.sip, self.dip)
                time.sleep(self._interval)
        except:
            print("close scapy!")
            t.stop()

    def sendInboundTraffic2Classifier(self, iface, sip, dip):
        smac = "00:00:00:00:00:01"
        dmac = "00:00:00:00:00:02"
        ether = Ether(src=smac, dst=dmac)
        ip = IP(src=sip, dst=dip)
        tcp = TCP(sport=1234, dport=80)
        data = "Hello World"
        frame = ether / ip / tcp /Raw(load=data)
        sendp(frame, iface=iface)

    def recvTraffic(self, iface, dmac, sip, dip):
        # sniff(
        t = AsyncSniffer(
            filter="ether dst " + str(dmac) +
                    " and ip", iface=iface, prn=self.frame_callback,
            count=0, store=0)
        return t

    def frame_callback(self, frame):
        frame.show()
        print("get frame")


if __name__=="__main__":
    argParser = ArgParser()
    iface = argParser.getArgs()['i']
    smac = argParser.getArgs()['smac']
    dmac = argParser.getArgs()['dmac']
    sip = argParser.getArgs()['sip']
    dip = argParser.getArgs()['dip']

    tsr = TriangleInBoundTrafficSendRecv(iface, dmac, sip, dip)
    tsr.start()
