#!/usr/bin/python

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

# # Classifier
# CLASSIFIER1_CONTROL_IP = "2.2.0.34"
# CLASSIFIER1_CONTROL_MAC = "01:92:16:81:21:01"

# CLASSIFIER2_CONTROL_IP = "2.2.1.34"
# CLASSIFIER2_CONTROL_MAC = "01:92:16:81:21:02"

# # BESS Server
# VNF1_CONTROL_IP = "2.2.0.66"
# VNF1_CONTROL_MAC = "01:92:16:81:21:06"

# VNF1_BACKUP_CONTROL_IP = "2.2.0.130"
# VNF1_BACKUP_CONTROL_MAC = "01:92:16:81:21:07"

# Websites server
WEBSITE1_IP = "2.2.0.34"
WEBSITE1_IP_PREFIX = 27
WEBSITE1_MAC = None
WEBSITE1_GATEWAY_IP = "2.2.0.33"

# Traffic generator
INGRESS_IP1 = "1.1.1.2"
INGRESS_IP1_PREFIX = 8
INGRESS_MAC1 = None

# Gateway
GATEWAY1_OUTBOUND_IP = "1.1.1.1"
GATEWAY1_OUTBOUND_IP_prefix = 8
GATEWAY1_OUTBOUND_MAC =  None

class TriangleTopo( Topo ):
    def build( self ):
        switchNum = 3

        # Create hosts
        hosts = [ self.addHost('h1'), self.addHost('h2'), self.addHost('h3'), self.addHost('h4')]

        # Create switches
        s1 = self.addSwitch('s1', dpid="0000000000000001", protocols=["OpenFlow13"])
        s2 = self.addSwitch('s2', dpid="0000000000000002", protocols=["OpenFlow13"])
        s3 = self.addSwitch('s3', dpid="0000000000000003", protocols=["OpenFlow13"])
        ## switches = [ self.addSwitch('s%s' %s, protocols=["OpenFlow13"]) for s in irange(1,switchNum) ]
        switches = [s1,s2,s3]

        # Wire up gateway peer nodes
        self.addLink( hosts[0],switches[0] )    # make sure the DCN gateway port 1 link to peer

        # Wire up switches
        for i in range(switchNum):
            print(i,(i+1)%switchNum)
            self.addLink(switches[i],switches[(i+1)%switchNum])

        # Wire up hosts
        self.addLink( hosts[1],switches[0] )
        self.addLink( hosts[2],switches[0] )
        self.addLink( hosts[3],switches[2] )

class NetConfigurator(object):
    def __init__(self,net):
        self._net = net

    def getNet(self):
        return self._net

    def showSwitchIntf(self):
        for s in self._net.switches:
            info("switch:",s," dpid: ", s.dpid, "'s intfList:\n")
            for intf in s.intfList():
                info("intf ",intf,"  mac:", intf.MAC() ,"  IP:",intf.IP(), "\n")
        info("\n")

    def showHostIntf(self):
        for h in self._net.hosts:
            info("host:",h,"'s intfList:\n")
            for intf in h.intfList():
                info("intf ",intf,"  mac:", intf.MAC() ,"  IP:",intf.IP(), "\n")
        info("\n")

    def showHostRoute(self):
        for h in self._net.hosts:
            info("host:",h,"'s route:\n")
            h.cmdPrint("route -n")
        info("\n")

    def configureSwitches(self):
        s1 = self._net.get('s1')
        s2 = self._net.get('s2')
        s3 = self._net.get('s3')

        # Add interface to switches
        self._addIntf2Switch(INT_TO_CLASSIFIER,s1)
        self._addIntf2Switch(INT_TO_VNF1,s2)
        self._addIntf2Switch(INTTOVNF1BACKUP,s3)

        # assign mac and ip address
        # config s1
        gateway1Intf = s1.intf('s1-eth1')
        GATEWAY1_OUTBOUND_MAC = gateway1Intf.MAC()
        # gateway1Intf.setIP( GATEWAY1_OUTBOUND_IP, prefixLen = GATEWAY1_OUTBOUND_IP_prefix )

    def configureHosts(self):
        # configure h1
        h1 = self._net.get('h1')
        # ip and mac address
        h1.setIP( INGRESS_IP1, prefixLen=INGRESS_IP1_PREFIX )
        INGRESS_MAC1 = h1.MAC()
        # default route
        s1 = self._net.get('s1')
        gateway1Intf = s1.intf('s1-eth1')
        defInt = h1.defaultIntf()
        defRoute = "dev " + str(defInt.name) + " via " + GATEWAY1_OUTBOUND_IP   # defRoute = "dev " + str(defInt.name) + " via " + str(gateway1Intf.IP() )
        h1.setDefaultRoute( defRoute )

        # configure h2
        h2 = self._net.get('h2')
        # ip and mac address
        h2.setIP( WEBSITE1_IP, prefixLen=WEBSITE1_IP_PREFIX )
        WEBSITE1_MAC = h2.MAC()
        # default route
        defInt = h2.defaultIntf()
        defRoute = "dev " + str(defInt.name) + " via " + WEBSITE1_GATEWAY_IP
        h2.setDefaultRoute( defRoute )

        # configure h3
        h3 = self._net.get('h3')
        # ip and mac address
        h3.setIP( "2.2.0.37", prefixLen=27 )
        HOST3_MAC = h3.MAC()
        # default route
        defInt = h3.defaultIntf()
        defRoute = "dev " + str(defInt.name) + " via " + WEBSITE1_GATEWAY_IP
        h3.setDefaultRoute( defRoute )

        # configure h4
        h4 = self._net.get('h4')
        # ip and mac address
        h4.setIP( "2.2.0.100", prefixLen=27 )
        HOST3_MAC = h4.MAC()
        # default route
        defInt = h4.defaultIntf()
        defRoute = "dev " + str(defInt.name) + " via " + "2.2.0.97"
        h4.setDefaultRoute( defRoute )

    def _checkIntf(self, intf ):
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
        info("\n")

    def _addIntf2Switch(self,intfName,switch):
        info( '*** Checking', intfName, '\n' )
        self._checkIntf( intfName )
        info( '*** Adding hardware interface', intfName, 'to switch',
            switch.name, '\n' )
        _intf = Intf(intfName, node=switch)
        info("\n")

if __name__ == '__main__':
    setLogLevel( 'info' )
    os.system("sudo mn -c")

    info( '*** Creating network\n' )
    topo = TriangleTopo()
    net = Mininet( topo=topo,
        controller=partial( RemoteController, ip='192.168.122.1', port=6633 )  )

    nc = NetConfigurator(net)
    nc.configureSwitches()
    nc.configureHosts()
    nc.showSwitchIntf()
    nc.showHostIntf()
    nc.showHostRoute()
    net = nc.getNet()

    info( '*** Start emulation\n' )
    net.start()
    CLI( net )
    net.stop()



topos = {
    'TriangleTopo': TriangleTopo
}