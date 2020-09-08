#!/usr/bin/python
# -*- coding: UTF-8 -*-

import random
import socket
import uuid

from ryu.topology.switches import Switch, Link, Host #, Port
# from ryu.controller.controller import Datapath
from ryu.lib import hub

from sam.base.command import *
from sam.test.testBase import *

class Datapath(object):
    def __init__(self, socket, address):
        self.socket = socket
        self.address = address
        self.is_active = True

        # The limit is arbitrary. We need to limit queue size to
        # prevent it from eating memory up.
        self.send_q = hub.Queue(16)
        self._send_q_sem = hub.BoundedSemaphore(self.send_q.maxsize)

        self.unreplied_echo_requests = []

        self.xid = random.randint(0, 100)
        self.id = None  # datapath_id is unknown yet
        self._ports = None
        self.state = None  # for pylint


class Port(object):
    # This is data class passed by EventPortXXX
    def __init__(self, dpid):
        super(Port, self).__init__()

        self.dpid = dpid
        self._ofproto = 11.1
        self._config = 11.1
        self._state = 11.1

        self.port_no = 11.1
        self.hw_addr = 11.1
        self.name = 11.1


class Sender(TestBase):
    def setup_TenThousandsServerDCNInfo(self):
        self.switches = []
        self.links = []
        self.hosts = []

        self.genSwitches()
        self.genLinks()
        self.genHosts()

    def genSwitch(self):
        switch = []
        for i in range(100):
            switch.append(1.1)
        return switch

    def genSwitches(self):
        s = socket.socket()
        address = "0.0.0.0"
        dp = Datapath(s, address)
        # switch = Switch(dp)
        switch = self.genSwitch()

        for i in range(1620):
            self.switches.append(switch)

    def genLinks(self):
        s = socket.socket()
        address = "0.0.0.0"
        dp = Datapath(s, address)
        # src = Switch(dp)
        # dst = Switch(dp)
        src = self.genSwitch()
        dst = self.genSwitch()
        # link = Link(src, dst)
        link = (src, dst)
        for i in range(46656):
            self.links.append(link)

    def genHosts(self):
        port = Port(1)
        host = Host("00:00:00:00:00:00", port)
        for i in range(10000):
            self.hosts.append(host)

    def sendGetServerSet(self):
        getServerCmdRply = self.genGetServerCmdRply()
        self.sendCmd(MEASURER_QUEUE, MSG_TYPE_MEDIATOR_CMD_REPLY, getServerCmdRply)

    def genGetServerCmdRply(self):
        cmdID = uuid.uuid1()
        attr = {'servers': self.hosts}
        cmdRply = CommandReply(CMD_TYPE_GET_SERVER_SET, cmdID, attr)
        return cmdRply

    def sendGetTopology(self):
        getTopologyCmdRply = self.genGetTopologyCmdRply()
        self.sendCmd(MEASURER_QUEUE, MSG_TYPE_MEDIATOR_CMD_REPLY, getTopologyCmdRply)

    def genGetTopologyCmdRply(self):
        cmdID = uuid.uuid1()
        attr = {'switches': self.switches, 'links': self.links}
        cmdRply = CommandReply(CMD_TYPE_GET_TOPOLOGY, cmdID, attr)
        return cmdRply

if __name__ == "__main__":
    s = Sender()
    s.setup_TenThousandsServerDCNInfo()
    s.sendGetServerSet()
    s.sendGetTopology()

