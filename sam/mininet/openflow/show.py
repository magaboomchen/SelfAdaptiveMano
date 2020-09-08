#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
3 switches topology
test ryu self learning switch
"""

import re
import sys
import os
from mininet.cli import CLI
from mininet.log import setLogLevel, info, error
from mininet.net import Mininet
from mininet.link import Intf
from mininet.topolib import TreeTopo
from mininet.util import quietRun
from functools import partial
from mininet.node import OVSSwitch, Controller, RemoteController
from mininet.topo import Topo
from mininet.util import irange, quietRun

# KVM Bridge
INT_TO_CLASSIFIER = 'eth1'
INT_TO_VNF1 = 'eth2'
INTTOVNF1BACKUP = 'eth3'

# Classifier
CLASSIFIER1_IP = "2.2.121.1"
CLASSIFIER1_MAC = "01:92:16:81:21:01"

CLASSIFIER2_IP = "2.2.121.2"
CLASSIFIER2_MAC = "01:92:16:81:21:02"

# BESS Server
VNF1_IP = "2.2.121.6"
VNF1_MAC = "01:92:16:81:21:06"

VNF1_BACKUP_IP = "2.2.121.7"
VNF1_BACKUP_MAC = "01:92:16:81:21:07"

# Websites server
WEBSITE1_IP = "2.2.121.4"
WEBSITE1_IP_PREFIX = 24
WEBSITE1_MAC = "01:92:16:81:21:04"

WEBSITE2_IP = "2.2.121.5"
WEBSITE2_IP_PREFIX = 24
WEBSITE2_MAC = "01:92:16:81:21:05"

# Traffic generator
INGRESS_IP1 = "122.122.122.3"
INGRESS_IP1_PREFIX = 8
IINGRESS_MAC1 = "01:22:12:21:22:03"

INGRESS_IP2 = "122.122.122.4"
INGRESS_IP2_PREFIX = 8
INGRESS_MAC2 = "01:22:12:21:22:04"

# Gateway
GATEWAY1_OUTBOUND_IP = "122.122.122.1"
GATEWAY1_OUTBOUND_IP_prefix = 8
GATEWAY1_OUTBOUND_MAC =  "01:22:12:21:22:01"

GATEWAY2_OUTBOUND_IP = "122.122.122.2"
GATEWAY2_OUTBOUND_IP_prefix = 8
GATEWAY2_OUTBOUND_MAC =  "01:22:12:21:22:02"

# SAM
SAM_IP = "2.2.121.3"
SAM_MAC = "01:92:16:81:21:03"

class GatewayTopo( Topo ):

    def build( self ):
        switchNum = 4

        # Create hosts and switches
        hosts = [ self.addHost('h1'), self.addHost('h2') ]
        switches = [ self.addSwitch('s%s' %s) for s in irange(1,switchNum) ]

        # Wire up switches
        for i in range(switchNum):
            self.addLink(switches[i],switches[(i+1)%switchNum])
        
        # Wire up hosts
        self.addLink( hosts[0],switches[0] )
        self.addLink( hosts[0],switches[switchNum-1] )
        self.addLink( hosts[1],switches[1] )

class NetConfigAgent(object):
    def __init__(self,net):
        self.net = net

    def getNet(self):
        return self.net

    def _addIntf2Switch(self,intfName,switch):
        info( '*** Adding hardware interface', intfName, 'to switch',
            switch.name, '\n' )
        _intf = Intf(intfName, node=switch)

    def configureSwitches(self):
        s1 = self.net.switches[0]   # DCN Gateway 1
        s2 = self.net.switches[1]   # VM3
        s3 = self.net.switches[2]   # VM4
        s4 = self.net.switches[3]   # DCN Gateway 2
        self._addIntf2Switch(INT_TO_CLASSIFIER,s1)
        self._addIntf2Switch(INT_TO_VNF1,s2)
        self._addIntf2Switch(INTTOVNF1BACKUP,s3)
        self._addIntf2Switch(INT_TO_CLASSIFIER,s4)

        # config s1
        # for intf in s1.intfList():
        #     info("s1.intfList: ", intf, '\n')
        gateway1Intf = s1.intf('s1-eth3')
        gateway1Intf.setMAC( GATEWAY1_OUTBOUND_MAC )
        gateway1Intf.setIP( GATEWAY1_OUTBOUND_IP, prefixLen = GATEWAY1_OUTBOUND_IP_prefix )

        # config s4
        gateway2Intf = s4.intf('s4-eth3')
        gateway2Intf.setMAC( GATEWAY2_OUTBOUND_MAC )
        gateway2Intf.setIP( GATEWAY2_OUTBOUND_IP, prefixLen = GATEWAY2_OUTBOUND_IP_prefix )

    def configureHosts(self):
        # configure h1: Ingress
        h1 = self.net.get('h1')

        # ip and mac address
        h1IntfList = h1.intfList()
        h1.setIP( INGRESS_IP1,prefixLen = INGRESS_IP1_PREFIX, intf = h1IntfList[0] )
        h1.setMAC( IINGRESS_MAC1 )
        h1.setIP( INGRESS_IP2,prefixLen = INGRESS_IP2_PREFIX, intf = h1IntfList[1] )
        h1.setMAC( INGRESS_MAC2 )

        s1 = self.net.switches[0]   # DCN Gateway 1
        gateway1Intf = s1.intf('s1-eth3')
        defInt = h1.defaultIntf()
        defRoute = "dev " + str(defInt.name) + " via " + str(gateway1Intf.IP() )
        info(defRoute,'\n')
        h1.setDefaultRoute( defRoute )
        info("default route of h1:", defRoute, '\n')

        # configure h2: Egress
        h2 = self.net.get('h2')

        # ip and mac address
        h2.setIP( WEBSITE1_IP,prefixLen=WEBSITE1_IP_PREFIX )
        h2.setMAC( WEBSITE1_MAC )

        # default route
        defInt = h2.defaultIntf()
        h2.setDefaultRoute(defInt)

        info( '*** Modified: the Mininet hosts:\n', self.net.hosts, '\n' )

    def checkIntf( intf ):
        "Make sure intf exists and is not configured."
        config = quietRun( 'ifconfig %s 2>/dev/null' % intf, shell=True )
        if not config:
            error( 'Error:', intf, 'does not exist!\n' )
            exit(1)
        ips = re.findall( r'\d+\.\d+\.\d+\.\d+', config )
        if ips:
            error( 'Error:', intf, 'has an IP address,'
                'and is probably in use!\n' )
            exit(1)

if __name__ == '__main__':
    os.system("sudo mn -c")
    setLogLevel( 'info' )
    info( '*** Creating network\n' )
    topo = GatewayTopo()
    net = Mininet( topo=topo,
        controller=partial( RemoteController, ip='192.168.122.1', port=6633 ))
    netConfigAgent = NetConfigAgent(net)
    netConfigAgent.configureSwitches()
    netConfigAgent.configureHosts()
    net = netConfigAgent.getNet()

    info( '*** Start emulation\n' )
    net.start()
    CLI( net )
    net.stop()

topos = {
    'GatewayTopo': GatewayTopo
}