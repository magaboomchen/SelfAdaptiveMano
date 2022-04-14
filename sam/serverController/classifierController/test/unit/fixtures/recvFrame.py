#!/usr/bin/python
# -*- coding: UTF-8 -*-

from scapy.all import sniff


def recvFrame(inIntf):
    sniff(filter="", iface=inIntf, prn=frame_callback, store=0, count=1)

def frame_callback(frame):
    frame.show() # debug statement

if __name__=="__main__":
    recvFrame("toClassifier")