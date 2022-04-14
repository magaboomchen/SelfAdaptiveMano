#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
This example shows how to add an interface (for example a real
hardware interface) to a network after the network is created.
"""

import re
import sys

from functools import partial
from mininet.cli import CLI
from mininet.log import setLogLevel, info, error
from mininet.net import Mininet
from mininet.link import Intf
from mininet.topolib import TreeTopo
from mininet.util import quietRun
from mininet.node import OVSSwitch, Controller, RemoteController

INTTOCLASSIFIER = 'eth1'
INTTOVNF1 = 'eth2'
INTTOVNF1BACKUP = 'eth3'

CLASSIFIERIP = "2.2.123.15"
CLASSIFIERMAC = "52:54:00:05:4d:7d"
VNF1IP = "2.2.124.87"
VNF1MAC = "52:54:00:9d:f4:f4"

def checkIntf( intf ):
    "Make sure intf exists and is not configured."
    config = quietRun( 'ifconfig %s 2>/dev/null' % intf, shell=True )
    if not config:
        error( 'Error:', intf, 'does not exist!\n' )
        exit( 1 )
    ips = re.findall( r'\d+\.\d+\.\d+\.\d+', config )
    if ips:
        error( 'Error:', intf, 'has an IP address,'
               'and is probably in use!\n' )
        exit( 1 )

def parse(sys):
    if len(sys.argv)==1:
        error( "Error: argument number error. ")
        exit(1)
   
    intfNameList = []
 
    # try to get hw intf from the command line
    for argIndex in range(len(sys.argv)):
        if argIndex == 0:
            continue
        else:
            intfName = sys.argv[argIndex] 
            info( '*** Connecting to hw intf: %s' % intfName )

            info( '*** Checking', intfName, '\n' )
            checkIntf( intfName )

            intfNameList.append(intfName)

    return intfNameList

def configureSwitches(net,intfNameList):
    switch = net.switches[ 0 ]
    for intfName in intfNameList:
        info( '*** Adding hardware interface', intfName, 'to switch',
              switch.name, '\n' )
        _intf = Intf( intfName, node=switch )

    info( '*** Note: you may need to reconfigure the interfaces for '
          'the Mininet hosts:\n', net.hosts, '\n' )

    return net

def configureHosts(net):
    # configure h1
    h1 = net.get('h1')

    # default route
    defInt = h1.defaultIntf()
    h1.setDefaultRoute(defInt)

    # arp
    h1.setARP( CLASSIFIERIP, CLASSIFIERMAC )
    h1.setARP( VNF1IP, VNF1MAC )

    return net

if __name__ == '__main__':
    setLogLevel( 'info' )
    intfNameList = parse(sys)
    info( '*** Creating network\n' )
    net = Mininet( topo=TreeTopo( depth=1, fanout=2 ),  controller=partial( RemoteController, ip='192.168.122.1', port=6633 )  )
    net = configureSwitches(net,intfNameList)
    net = configureHosts(net)
    net.start()
    CLI( net )
    net.stop()
