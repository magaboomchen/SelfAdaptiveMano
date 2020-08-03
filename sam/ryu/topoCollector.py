from ryu.base import app_manager
from ryu.controller import mac_to_port
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.topology.api import get_switch, get_link
from ryu.app.wsgi import ControllerBase
from ryu.topology import event, switches 
from ryu.controller import event as controllerEvent

import logging
from sam.ryu.baseApp import BaseApp

class TopologyChangeEvent(controllerEvent.EventBase):
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
        self.logger.setLevel(logging.INFO)
        self.logger.warning("Please use'ryu-manager --observe-links topoCollector.py'")

    def _printSwitches(self):
        for switch in self.switches.itervalues():
            print(switch)

    def _printLinks(self):
        for link in self.links.itervalues():
            print(link)

    def _printHosts(self):
        for host in self.hosts.itervalues():
            print(host)

    def _sendEvent(self, ev):
        self.logger.info('*** Send event: %s' %(ev.__class__.__name__))
        self.send_event_to_observers(ev)

    @set_ev_cls(event.EventSwitchEnter)
    def _addSwitch(self,ev):
        switch = ev.switch
        self.switches[switch.dp.id] = switch
        self.logger.info("add switch: ")
        print(switch)
        self._sendEvent(TopologyChangeEvent())
        # self._ls(switch)
        # self._ls(switch.ports)
        # print(switch.to_dict())
        # print(type(switch.ports))
        # for port in switch.ports:
        #     print(port)
        #     self._ls(port)
        #     pass

    @set_ev_cls(event.EventSwitchLeave)
    def _delSwitch(self,ev):
        switch = ev.switch
        del self.switches[switch.dp.id]
        self.logger.info("delete switch: ")
        print(switch)
        self._sendEvent(TopologyChangeEvent())

    @set_ev_cls(event.EventLinkAdd)
    def _addLink(self,ev):
        link = ev.link
        self.links[(link.src.dpid,link.dst.dpid)] = link
        self.logger.info("add link: ")
        print(link)
        self._sendEvent(TopologyChangeEvent())

    @set_ev_cls(event.EventLinkDelete)
    def _delLink(self,ev):
        link = ev.link
        del self.links[(link.src.dpid,link.dst.dpid)]
        self.logger.info("del link: ")
        print(link)
        self._sendEvent(TopologyChangeEvent())

    @set_ev_cls(event.EventHostAdd)
    def _addHost(self,ev):
        host = ev.host
        self.hosts[host.mac] = host
        self.logger.info("add host")
        print(host)

    @set_ev_cls(event.EventHostMove)
    def _moveHost(self,ev):
        host = ev.host
        self.hosts[host.mac] = host
        self.logger.info("move host")
        print(host)

    @set_ev_cls(event.EventHostDelete)
    def _delHost(self,ev):
        # Note: Currently, EventHostDelete will never be raised, because we have no
        # appropriate way to detect the disconnection of hosts. Just defined for
        # future use.
        pass