#!/usr/bin/python
# -*- coding: UTF-8 -*-

import random
import uuid

from sam.base.command import *
from sam.base.switch import *
from sam.base.server import *
from sam.base.link import *
from sam.test.testBase import *


class TestMeasurerClass(TestBase):
    def setup_TenThousandsServerDCNInfo(self):
        self.switches = self.genSwitchList(1620,
            SWITCH_TYPE_SFF, range(1620))
        self.links = self.genLinkList(46656)
        self.servers = []
        self.servers.extend(
            self.genServerList(1, SERVER_TYPE_CLASSIFIER,
            ["2.2.0.36"], ["2.2.0.35"], [SERVERID_OFFSET])
        )
        self.servers.extend(
            self.genServerList(1, SERVER_TYPE_NORMAL,
            ["2.2.0.34"], ["2.2.0.34"], [SERVERID_OFFSET+1])
        )
        self.servers.extend(
            self.genServerList(3, SERVER_TYPE_NFVI,
            ["2.2.0.69", "2.2.0.71", "2.2.0.99"],
            ["2.2.0.68", "2.2.0.70", "2.2.0.98"],
            range(SERVERID_OFFSET+2,SERVERID_OFFSET+2+3))
        )

    def sendGetServerSetCmdRply(self):
        getServerCmdRply = self.genGetServerCmdRply()
        self.sendCmdCmdRply(MEASURER_QUEUE, MSG_TYPE_MEDIATOR_CMD_REPLY,
            getServerCmdRply)

    def genGetServerCmdRply(self):
        cmdID = uuid.uuid1()
        attr = {'servers': self.hosts}
        cmdRply = CommandReply(CMD_TYPE_GET_SERVER_SET, cmdID, attr)
        return cmdRply

    def sendGetTopologyCmdRply(self):
        getTopologyCmdRply = self.genGetTopologyCmdRply()
        self.sendCmdCmdRply(MEASURER_QUEUE, MSG_TYPE_MEDIATOR_CMD_REPLY,
            getTopologyCmdRply)

    def genGetTopologyCmdRply(self):
        cmdID = uuid.uuid1()
        attr = {'switches': self.switches, 'links': self.links}
        cmdRply = CommandReply(CMD_TYPE_GET_TOPOLOGY, cmdID, attr)
        return cmdRply
