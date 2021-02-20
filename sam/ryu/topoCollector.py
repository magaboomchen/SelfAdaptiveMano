#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging

from ryu.base import app_manager
from ryu.controller import mac_to_port
from ryu.controller import ofp_event
from ryu.controller import event as ryuControllerEvent
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.topology.api import get_switch, get_link
from ryu.topology import event, switches 
from ryu.app.wsgi import ControllerBase

from sam.ryu.baseApp import BaseApp
from sam.base.command import *
from sam.base.messageAgent import *
from sam.base.switch import *
from sam.base.server import *
from sam.base.link import Link


class TopologyChangeEvent(ryuControllerEvent.EventBase):
    def __init__(self):
        super(TopologyChangeEvent, self).__init__()


class TopoCollector(BaseApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _EVENTS = [TopologyChangeEvent]

    def __init__(self, *args, **kwargs):
        super(TopoCollector, self).__init__(*args, **kwargs)
        self.topology_api_app = self
        self.switches = {}
        self.links = {}
        self.hosts = {}

        # following member record all device in history with current state, i.e. active/inactive
        self.switchesInfo = {}
        self.linksInfo = {}

        self.logger.setLevel(logging.WARNING)
        self.logger.warning("Please use'ryu-manager --observe-links topoCollector.py'")

    def _printSwitches(self):
        for switch in self.switches.itervalues():
            self.logger.info("switch:{0}".format(switch))

    def _printLinks(self):
        for link in self.links.itervalues():
            self.logger.info("link:{0}".format(link))

    def _printHosts(self):
        for host in self.hosts.itervalues():
            self.logger.info("host:{0}".format(host))

    def _sendEvent(self, ev):
        self.logger.info('*** Send event: %s' %(ev.__class__.__name__))
        self.send_event_to_observers(ev)

    @set_ev_cls(event.EventSwitchEnter)
    def _addSwitch(self,ev):
        switch = ev.switch
        self.switches[switch.dp.id] = switch
        self.logger.info("add switch:{0}".format(switch))
        self.switchesInfo[switch.dp.id] = {'switch':switch, 'Active':True}
        self._sendEvent(TopologyChangeEvent())
        # self._ls(switch)
        # self._ls(switch.ports)
        self.logger.debug(switch.to_dict())
        self.logger.debug(type(switch.ports))
        for port in switch.ports:
            self.logger.debug(port)
            # self._ls(port)

    @set_ev_cls(event.EventSwitchLeave)
    def _delSwitch(self,ev):
        switch = ev.switch
        del self.switches[switch.dp.id]
        self.switchesInfo[switch.dp.id]['Active'] = False
        self.logger.info("delete switch:{0}".format(switch))
        self._sendEvent(TopologyChangeEvent())

    @set_ev_cls(event.EventLinkAdd)
    def _addLink(self,ev):
        link = ev.link
        self.links[(link.src.dpid,link.dst.dpid)] = link
        self.linksInfo[(link.src.dpid,link.dst.dpid)] = {'link':link, 'Active':True}
        self.logger.info("add link:{0}".format(link))
        self._sendEvent(TopologyChangeEvent())

    @set_ev_cls(event.EventLinkDelete)
    def _delLink(self,ev):
        link = ev.link
        del self.links[(link.src.dpid,link.dst.dpid)]
        self.linksInfo[(link.src.dpid,link.dst.dpid)]['Active'] = False
        self.logger.info("del link:{0}".format(link))
        self._sendEvent(TopologyChangeEvent())

    @set_ev_cls(event.EventHostAdd)
    def _addHost(self,ev):
        host = ev.host
        self.hosts[host.mac] = host
        self.logger.info("add host:{0}".format(host))

    @set_ev_cls(event.EventHostMove)
    def _moveHost(self,ev):
        host = ev.host
        self.hosts[host.mac] = host
        self.logger.info("move host:{0}".format(host))

    @set_ev_cls(event.EventHostDelete)
    def _delHost(self,ev):
        # Note: Currently, EventHostDelete will never be raised,
        # because we have no appropriate way to detect the disconnection
        # of hosts.
        # Just defined for future use.
        pass

    def get_topology_handler(self, cmd):
        self.logger.info(
            '*** TopoCollector App Received command={0}'.format(cmd)
            )
        attr = {
            "switches": self._transSwitches(self.switchesInfo),
            "links": self._transLinks(self.linksInfo),
            # "servers": self._transHosts(self.hosts)
        }
        attr.update(cmd.attributes)
        cmdRply = CommandReply(cmd.cmdID, CMD_STATE_SUCCESSFUL, attr)
        rplyMsg = SAMMessage(MSG_TYPE_NETWORK_CONTROLLER_CMD_REPLY, cmdRply)
        queue = MEDIATOR_QUEUE
        self._messageAgent.sendMsg(queue, rplyMsg)

    def _transSwitches(self, switchesInfo):
        # switchList = []
        switchDict = {}
        for switchID,switchInfoDict in switchesInfo.items():
            switch = switchInfoDict['switch']
            # self._ls(switch.address)
            self.logger.info(
                "switch:dpid:{0},address:{1}".format(
                    switch.dp.id, switch.dp.address
                )
            )
            dpid = switch.dp.id
            sw = Switch(dpid, self._switchConfs[dpid].switchType,
                self._switchConfs[dpid].lANNet)
            switchState = switchInfoDict['Active']
            switchDict[dpid] = {'switch':sw, 'Active':switchState}
        return switchDict

    def _transLinks(self, linksInfo):
        linkDict = {}
        for linkID, linkInfo in linksInfo.items():
            link = linkInfo['link']
            # self._ls(link)
            self.logger.info(
                "link:({0},{1})".format(
                    link.src.dpid,link.dst.dpid
                    )
                )
            linkState = linkInfo['Active']
            linkDict[(link.src.dpid,link.dst.dpid)] = {
                'link': Link(link.src.dpid, link.dst.dpid),
                'Active': linkState
                }
        return linkDict

    # def _transHosts(self, hosts):
    #     serverList = []
    #     for host in self.hosts.values():
    #         # self._ls(host)
    #         self.logger.info(
    #             "ipv4:{0},ipv6:{1},mac:{2},port:{3}".format(
    #                 host.ipv4, host.ipv6, host.mac, host.port
    #             )
    #         )
    #         server = Server(None, host.ipv4, SERVER_TYPE_NORMAL)
    #         serverList.append(server)
    #     return serverList
