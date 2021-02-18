#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
3 switches topology
test UFFR/NotVia-PSFC/End-to-endProtection
"""

import re
import sys
import os
import time
from signal import SIGINT

from mininet.cli import CLI
from mininet.log import setLogLevel, info, error
from mininet.net import Mininet
from mininet.link import Intf
from mininet.topolib import TreeTopo
from mininet.util import quietRun
from mininet.node import OVSSwitch, Controller, RemoteController
from mininet.topo import Topo
from mininet.link import TCLink
from mininet.util import irange, quietRun, pmonitor
from functools import partial

from sam.base.messageAgent import *
from sam.base.command import *
from sam.test.FRR.test3InBoundTrafficSendRecv import *

# KVM Bridge
INT_TO_CLASSIFIER = 'eth1'
INT_TO_VNF1 = 'eth2'
INT_TO_VNF1BACKUP = 'eth3'
INT_TO_VNF1BACKUP0 = "eth4"

# Websites server
# WEBSITE1_IP = "2.2.0.34"
WEBSITE1_IP = "3.3.3.3"
WEBSITE1_IP_PREFIX = 27
WEBSITE1_MAC = None
WEBSITE1_GATEWAY_IP = "2.2.0.33"

# Traffic generator
INGRESS_IP1 = "1.1.1.2"
INGRESS_IP1_PREFIX = 8
INGRESS_MAC1 = None
INGRESS_INTERFACE_NAME = None

# Gateway
GATEWAY1_OUTBOUND_IP = "1.1.1.1"
GATEWAY1_OUTBOUND_IP_prefix = 8
GATEWAY1_OUTBOUND_MAC =  None

# test mode
MODE_UFRR = "0"
MODE_NOTVIA_REMAPPING = "1"
MODE_NOTVIA_PSFC = "2"
MODE_END2END_PROTECTION = "3"
MODE_DIRECT_REMAPPING = "4"
MODE_SEND_RECV_INBOUND_TRAFFIC = "5"


class TriangleTopo( Topo ):
    def build( self ):
        switchNum = 3

        # Create hosts
        hosts = [ self.addHost('h1'),
            self.addHost('h2'), self.addHost('h3'), self.addHost('h4')]

        # Create switches
        s1 = self.addSwitch('s1', dpid="0000000000000001",
            protocols=["OpenFlow13"])
        s2 = self.addSwitch('s2', dpid="0000000000000002",
            protocols=["OpenFlow13"])
        s3 = self.addSwitch('s3', dpid="0000000000000003",
            protocols=["OpenFlow13"])
        switches = [s1,s2,s3]

        # Wire up gateway peer nodes
        self.addLink(hosts[0], switches[0])
        # make sure the DCN gateway port 1 link to peer

        # Wire up switches
        # for i in range(switchNum):
        #     print(i,(i+1)%switchNum)
        #     self.addLink(switches[i],switches[(i+1)%switchNum])
        self.addLink(switches[0], switches[1], delay='10ms')
        self.addLink(switches[1], switches[2], delay='10ms')
        self.addLink(switches[2], switches[0], delay='10ms')

        # Wire up hosts
        self.addLink( hosts[1],switches[0])
        self.addLink( hosts[2],switches[0])
        self.addLink( hosts[3],switches[2])

class NetConfigurator(object):
    def __init__(self,net):
        self._net = net

    def getNet(self):
        return self._net

    def showSwitchIntf(self):
        for s in self._net.switches:
            info("switch:", s, " dpid: ", s.dpid, "'s intfList:\n")
            for intf in s.intfList():
                info("intf ", intf, "  mac:", intf.MAC(),
                    "  IP:", intf.IP(), "\n")
        info("\n")

    def showHostIntf(self):
        for h in self._net.hosts:
            info("host:", h, "'s intfList:\n")
            for intf in h.intfList():
                info("intf ", intf, "  mac:", intf.MAC(),
                    "  IP:", intf.IP(), "\n")
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
        self._addIntf2Switch(INT_TO_CLASSIFIER, s1)
        self._addIntf2Switch(INT_TO_VNF1, s2)
        self._addIntf2Switch(INT_TO_VNF1BACKUP0, s2)
        self._addIntf2Switch(INT_TO_VNF1BACKUP, s3)

        # assign mac and ip address
        # config s1
        gateway1Intf = s1.intf('s1-eth1')
        GATEWAY1_OUTBOUND_MAC = gateway1Intf.MAC()

    def configureHosts(self):
        # configure h1
        h1 = self._net.get('h1')
        # ip and mac address
        h1.setIP(INGRESS_IP1, prefixLen=INGRESS_IP1_PREFIX)
        global INGRESS_MAC1
        INGRESS_MAC1 = h1.MAC()
        # default route
        s1 = self._net.get('s1')
        gateway1Intf = s1.intf('s1-eth1')
        defInt = h1.defaultIntf()
        global INGRESS_INTERFACE_NAME
        INGRESS_INTERFACE_NAME = str(defInt.name)
        defRoute = "dev " + str(defInt.name) + " via " + GATEWAY1_OUTBOUND_IP
        h1.setDefaultRoute( defRoute )

        # configure h2
        h2 = self._net.get('h2')
        # ip and mac address
        h2.setIP(WEBSITE1_IP, prefixLen=WEBSITE1_IP_PREFIX)
        global WEBSITE1_MAC
        WEBSITE1_MAC = h2.MAC()
        # default route
        defInt = h2.defaultIntf()
        defRoute = "dev " + str(defInt.name) + " via " + WEBSITE1_GATEWAY_IP
        h2.setDefaultRoute( defRoute )

        # configure h3
        h3 = self._net.get('h3')
        # ip and mac address
        h3.setIP("2.2.0.37", prefixLen=27)
        HOST3_MAC = h3.MAC()
        # default route
        defInt = h3.defaultIntf()
        defRoute = "dev " + str(defInt.name) + " via " + WEBSITE1_GATEWAY_IP
        h3.setDefaultRoute( defRoute )

        # configure h4
        h4 = self._net.get('h4')
        # ip and mac address
        h4.setIP("2.2.0.100", prefixLen=27)
        HOST3_MAC = h4.MAC()
        # default route
        defInt = h4.defaultIntf()
        defRoute = "dev " + str(defInt.name) + " via " + "2.2.0.97"
        h4.setDefaultRoute( defRoute )

    def _checkIntf(self, intf ):
        "Make sure intf exists and is not configured."
        config = quietRun('ifconfig %s 2>/dev/null' % intf, shell=True)
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
        info('*** Checking', intfName, '\n')
        self._checkIntf( intfName )
        info('*** Adding hardware interface', intfName, 'to switch',
            switch.name, '\n')
        _intf = Intf(intfName, node=switch)
        info("\n")


class ManoTester(object):
    def __init__(self, net):
        self.net = net
        self.outfiles = {}
        self.errfiles = {}
        self.filePath = "/home/vm2/Projects/SelfAdaptiveMano/sam/test/FRR/"
        self.SLEEP_TIME = 8
        self.INTERVAL = 0.5
        self._messageAgent = MessageAgent()

    def startTest(self):
        while True:
            print(
                    "Mode {0}: UFRR\n"
                    "Mode {1}: NotVia + Remapping\n"
                    "Mode {2}: NotVia + PSFC\n"
                    "Mode {3}: End-to-end Protection\n"
                    "Mode {4}: Direct Remapping\n"
                    "Mode {5}: send and recv inbound traffic\n"
                    "cli: start interactive cli\n"
                    "quit: to quit".format(
                        MODE_UFRR,
                        MODE_NOTVIA_REMAPPING,
                        MODE_NOTVIA_PSFC,
                        MODE_END2END_PROTECTION,
                        MODE_DIRECT_REMAPPING,
                        MODE_SEND_RECV_INBOUND_TRAFFIC
                    )
                )
            print("Please input the mode number:")
            self.mode = raw_input()
            if self.mode in [
                MODE_UFRR,
                MODE_NOTVIA_REMAPPING,
                MODE_NOTVIA_PSFC,
                MODE_END2END_PROTECTION
            ]:
                self.testHandler()
            elif self.mode == MODE_DIRECT_REMAPPING:
                self.sendReMappingCmd()
            elif self.mode == MODE_SEND_RECV_INBOUND_TRAFFIC:
                self.sendRecvInBoundTraffic()
            elif self.mode == "cli":
                CLI(self.net)
            elif self.mode == "quit":
                break
            else:
                print("Your input is {0}".format(self.mode))
                continue

    def testHandler(self):
        h1 = self.net.get('h1')
        h2 = self.net.get('h2')
        self.stabilizeNetwork(h1, h2)
        # self.startMeasureThroughput(h1, h2)
        self.startMeasureDropRate(h1, h2)
        # time.sleep(self.SLEEP_TIME) # wait for drop rate measurement program
        self.startMeasureE2EDelay(h1, h2)
        time.sleep(self.SLEEP_TIME)
        self.disableLink('s1','s2')
        time.sleep(self.SLEEP_TIME)
        self.enableLink('s1','s2')
        time.sleep(self.SLEEP_TIME)
        s2 = self.net.get('s2')
        self.disableDpdkServer(s2, 'eth2')
        if self.mode == MODE_NOTVIA_REMAPPING:
            self.sendReMappingCmd()
        time.sleep(self.SLEEP_TIME * 2)
        self.endMeasureE2EDelay(h1, h2)
        # self.endMeasureThroughput(h1, h2)
        self.endMeasureDropRate(h1, h2)
        self.enableDpdkServer(s2, 'eth2')

    def stabilizeNetwork(self, src, dst):
        src.cmdPrint(
                    'ping '+dst.IP()+' -c 5 -i 0.2 ',
                    '&' )

    def addOurputFiles(self, host, fileName):
        if not self.outfiles.has_key(host):
            self.outfiles[host] = {}
        if not self.outfiles[host].has_key(fileName):
            self.outfiles[host][fileName] = self.filePath\
                + fileName + '_{0}.out'.format(host.name)
        if not self.errfiles.has_key(host):
            self.errfiles[host] = {}
        if not self.errfiles[host].has_key(fileName):
            self.errfiles[host][fileName] = self.filePath + fileName\
                + '_{0}.err'.format(host.name)

    def startMeasureDropRate(self, src, dst):
        self.addOurputFiles(src, "iperf3udp")
        self.addOurputFiles(dst, "iperf3udp")
        # print("dst start iperf3 server")
        dst.cmdPrint('iperf3 -s -i ' + str(self.INTERVAL),
                    '>', self.outfiles[dst]["iperf3udp"],
                    '2>', self.errfiles[dst]["iperf3udp"],
                    '&' )
        # print("src start iperf3 client")
        src.cmdPrint(
                    'iperf3 -c ' + dst.IP() + ' -M 1420 -u --length 1420 -i ' + str(self.INTERVAL) + ' -t ' + str(self.SLEEP_TIME * 7),
                    '>', self.outfiles[src]["iperf3udp"],
                    '2>', self.errfiles[src]["iperf3udp"],
                    '&' )

    def endMeasureDropRate(self, src, dst):
        print("endMeasureDropRate")
        src.cmd('killall iperf3')
        dst.cmd('killall iperf3')

    def startMeasureThroughput(self, src, dst):
        self.addOurputFiles(src, "iperf3")
        self.addOurputFiles(dst, "iperf3")
        # print("dst start iperf3 server")
        dst.cmdPrint('iperf3 -s -i ' + str(self.INTERVAL),
                    '>', self.outfiles[dst]["iperf3"],
                    '2>', self.errfiles[dst]["iperf3"],
                    '&' )
        # print("src start iperf3 client")
        src.cmdPrint(
                    'iperf3 -c ' + dst.IP() + ' -M 1420 -i ' + str(self.INTERVAL) + ' -t ' + str(self.SLEEP_TIME * 7),
                    '>', self.outfiles[src]["iperf3"],
                    '2>', self.errfiles[src]["iperf3"],
                    '&' )

    def endMeasureThroughput(self, src, dst):
        print("endMeasureDropRate")
        src.cmd('killall iperf3')
        dst.cmd('killall iperf3')

    def startMeasureE2EDelay(self, src, dst):
        self.addOurputFiles(src, "ping")
        self.addOurputFiles(dst, "ping")
        # print("src start ping")
        src.cmdPrint(
                    'ping '+dst.IP()+' -i ' + str(self.INTERVAL),
                    '>', self.outfiles[src]["ping"],
                    '2>', self.errfiles[src]["ping"],
                    '&' )

    def endMeasureE2EDelay(self, src, dst):
        print("endMeasureE2EDelay")
        src.cmd('killall ping')

    def enableLink(self, s1Name, s2Name):
        print("enableLink")
        self.net.configLinkStatus(s1Name, s2Name, "up")

    def disableLink(self, s1Name, s2Name):
        print("disableLink")
        self.net.configLinkStatus(s1Name, s2Name, "down")

    def enableDpdkServer(self, switch, intfName):
        print("enableDpdkServer")
        switch.cmd('ip link set dev ' + intfName + ' up')

    def disableDpdkServer(self, switch, intfName):
        print("disableDpdkServer")
        switch.cmd('ip link set dev ' + intfName + ' down')

    def sendReMappingCmd(self):
        print("sendReMappingCmd")
        msg = SAMMessage(MSG_TYPE_TESTER_CMD, Command(
            cmdType=CMD_TYPE_TESTER_REMAP_SFCI, cmdID=uuid.uuid1()))
        self._messageAgent.sendMsg(MININET_TESTER_QUEUE, msg)

    def sendRecvInBoundTraffic(self):
        try:
            print("sendRecvInBoundTraffic")
            print("iface:{0}, dmac:{1}, sip:{2}, dip:{3}".format(
                INGRESS_INTERFACE_NAME, INGRESS_MAC1, INGRESS_IP1, WEBSITE1_IP
            ))
            h1 = self.net.get('h1')
            h1.cmdPrint("sudo python ./test3InBoundTrafficSendRecv.py"
                " -i {0} -dmac {1}".format(INGRESS_INTERFACE_NAME, INGRESS_MAC1))
            # tsr = Test3InBoundTrafficSendRecv(iface=INGRESS_INTERFACE_NAME,
            #     dmac=INGRESS_MAC1, sip=INGRESS_IP1, dip=WEBSITE1_IP)
            # tsr.start()
        except:
            print("stop send recv!")


if __name__ == '__main__':
    setLogLevel( 'info' )
    os.system("sudo mn -c")

    info( '*** Creating network\n' )
    topo = TriangleTopo()
    net = Mininet( topo=topo,
        controller=partial(RemoteController,
            ip='192.168.122.1',
            port=6633),
        link=TCLink)

    nc = NetConfigurator(net)
    nc.configureSwitches()
    nc.configureHosts()
    nc.showSwitchIntf()
    nc.showHostIntf()
    nc.showHostRoute()
    net = nc.getNet()

    info( '*** Start emulation\n' )
    net.start()
    mT = ManoTester(net)
    mT.startTest()
    net.stop()


topos = {
    'TriangleTopo': TriangleTopo
}

