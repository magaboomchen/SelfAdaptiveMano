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

INTTOCLASSIFIER = 'eth1'
INTTOVNF1 = 'eth2'
INTTOVNF1BACKUP = 'eth3'

CLASSIFIERIP = "10.0.0.1"
CLASSIFIERMAC = "52:54:00:05:4d:7d"

VNF1IP = "10.0.0.2"
VNF1MAC = "52:54:00:9d:f4:f4"

VNF1BackupIP = "10.0.0.3"
VNF1BackupMAC = "52:54:00:f7:34:25"

EGRESSIP = "10.0.0.4"
EGRESSIPPREFIX = 8
EGRESSMAC = "52:54:36:22:34:25"

class TriangleTopo( Topo ):

    def build( self ):
        # Create hosts and switches
        hosts = [ self.addHost('h1') ]
        switches = [ self.addSwitch('s%s' %s) for s in irange(1,3) ]

        # Wire up switches
        for i in range(3):
            print(i,(i+1)%3)
            self.addLink(switches[i],switches[(i+1)%3])
        
        # Wire up hosts
        self.addLink( hosts[0],switches[0] )



class NetConfigAgent():
    def __init__(self,net,intfNameList):
        self.net = net
        self.intfNameList = intfNameList

    def getNet(self):
        return self.net

    def configureSwitches(self):
        for index in range( len(self.intfNameList) ):
            switch = self.net.switches[ index ]
            intfName = self.intfNameList[index]
            info( '*** Adding hardware interface', intfName, 'to switch',
                switch.name, '\n' )
            _intf = Intf( intfName, node=switch )

        info( '*** Note: you may need to reconfigure the interfaces for '
            'the Mininet hosts:\n', self.net.hosts, '\n' )

    def configureHosts(self):
        # configure h1
        h1 = self.net.get('h1')

        # ip and mac address
        h1.setIP( EGRESSIP,prefixLen=EGRESSIPPREFIX )
        h1.setMAC( EGRESSMAC )

        # default route
        defInt = h1.defaultIntf()
        h1.setDefaultRoute(defInt)

        # arp TODO:delete this arp and use gratious arp app instead later
        h1.setARP( CLASSIFIERIP, CLASSIFIERMAC )
        h1.setARP( VNF1IP, VNF1MAC )
        h1.setARP( VNF1BackupIP, VNF1BackupMAC )

        info( '*** Modified: the Mininet hosts:\n', self.net.hosts, '\n' )

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



if __name__ == '__main__':
    os.system("sudo mn -c")

    setLogLevel( 'info' )
    info( '*** Creating network\n' )
    topo = TriangleTopo()
    net = Mininet( topo=topo,
        controller=partial( RemoteController, ip='192.168.122.1', port=6633 )  )
    intfNameList = ['eth1','eth2','eth3']
    netConfigAgent = NetConfigAgent(net,intfNameList)
    netConfigAgent.configureSwitches()
    netConfigAgent.configureHosts()
    net = netConfigAgent.getNet()

    info( '*** Start emulation\n' )
    net.start()
    CLI( net )
    net.stop()



topos = {
    'TriangleTopo': TriangleTopo
}