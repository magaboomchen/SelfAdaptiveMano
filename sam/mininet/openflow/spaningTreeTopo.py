#!/usr/bin/python
# -*- coding: UTF-8 -*-

from mininet.cli import CLI
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.term import makeTerm


if '__main__' == __name__:
    net = Mininet(controller=RemoteController)

    c0 = net.addController('c0', ip='192.168.122.1', port=6633)

    s1 = net.addSwitch('s1', protocols=["OpenFlow13"])
    s2 = net.addSwitch('s2', protocols=["OpenFlow13"])
    s3 = net.addSwitch('s3', protocols=["OpenFlow13"])

    h1 = net.addHost('h1')
    h2 = net.addHost('h2')
    h3 = net.addHost('h3')

    net.addLink(s1, h1)
    net.addLink(s2, h2)
    net.addLink(s3, h3)

    net.addLink(s1, s2)
    net.addLink(s2, s3)
    net.addLink(s3, s1)

    net.build()
    c0.start()
    s1.start([c0])
    s2.start([c0])
    s3.start([c0])

    #net.startTerms()

    CLI(net)

    net.stop()