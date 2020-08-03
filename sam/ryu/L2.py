from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import arp
from ryu.lib.packet import ether_types
from ryu.topology import event, switches 
from ryu.controller import dpset

import logging
from sam.ryu.topoCollector import TopoCollector
from conf.genSwitchConf import SwitchConf
from conf.ryuConf import *
from sam.ryu.baseApp import BaseApp

class L2(BaseApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {
        'dpset': dpset.DPSet,
        'TopoCollector': TopoCollector
        }

    def __init__(self, *args, **kwargs):
        super(L2, self).__init__(*args, **kwargs)
        self.dpset = kwargs['dpset']
        self.topoCollector = kwargs['TopoCollector']
        
        self._localPortTable = {}    # {switchid:{port1,port2}}
        self._peerPortTable = {}
        self._switchesLANMacTable = {}

        self.logger.setLevel(logging.WARNING)

    def _addLocalPort(self, datapath, port):
        if self._localPortTable.has_key(datapath.id):
            if self._localPortTable[datapath.id].has_key(port.port_no):
                return 
        else:
            self._localPortTable[datapath.id] = {}

        self._localPortTable[datapath.id][port.port_no] = port
        portMac = port.hw_addr

        parser = datapath.ofproto_parser
        match = parser.OFPMatch(eth_dst=portMac,eth_type=ether_types.ETH_TYPE_IP)
        inst = [parser.OFPInstructionGotoTable(table_id = CLASSIFIER_TABLE)]
        self._add_flow(datapath, match, inst, table_id = MAIN_TABLE, priority = 1)

    def _delLocalPort(self, datapath, port):
        if self._localPortTable.has_key(datapath.id):
            if not self._localPortTable[datapath.id].has_key(port.port_no):
                return 
        else:
            return 

        del self._localPortTable[datapath.id][port.port_no]
        portMac = port.hw_addr

        parser = datapath.ofproto_parser
        match = parser.OFPMatch(eth_dst=portMac,eth_type=ether_types.ETH_TYPE_IP)
        self._del_flow(datapath, match, table_id = MAIN_TABLE, priority = 1)

    def _addPeerPort(self, datapath, link):
        localPort = link.src
        peerPort = link.dst

        if self._peerPortTable.has_key(datapath.id):
            if self._peerPortTable[datapath.id].has_key(peerPort.port_no):
                return 
        else:
            self._peerPortTable[datapath.id] = {}

        self._peerPortTable[datapath.id][peerPort.port_no] = link
        peerPortMac = peerPort.hw_addr

        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch(eth_dst=peerPortMac)
        actions = [parser.OFPActionOutput(localPort.port_no)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,actions)]
        self._add_flow(datapath, match, inst, table_id = L2_TABLE, priority = 1)

    def _delPeerPort(self, datapath, link):
        localPort = link.src
        peerPort = link.dst

        if self._peerPortTable.has_key(datapath.id):
            if not self._peerPortTable[datapath.id].has_key(peerPort.port_no):
                return 
        else:
            return 

        del self._peerPortTable[datapath.id][peerPort.port_no]
        peerPortMac = peerPort.hw_addr

        parser = datapath.ofproto_parser
        match = parser.OFPMatch(eth_dst=peerPortMac)
        self._del_flow(datapath, match, table_id = L2_TABLE, priority = 1)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        inst = [parser.OFPInstructionGotoTable(table_id = L2_TABLE)]
        self._add_flow(datapath, match, inst, table_id = MAIN_TABLE, priority=0)

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        self._add_flow(datapath, match, inst, table_id = L2_TABLE, priority=0)

        match = parser.OFPMatch(
                eth_type=ether_types.ETH_TYPE_ARP
            )
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        self._add_flow(datapath, match, inst, table_id = L2_TABLE, priority=2)

        self._switchesLANMacTable[datapath.id] = {}

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def _port_status_handler(self, ev):
        msg = ev.msg
        reason = msg.reason
        port_no = msg.desc.port_no
        datapath = msg.datapath
        dpid = datapath.id
        ofproto = datapath.ofproto
        port = msg.desc

        if reason == ofproto.OFPPR_ADD:
            self.logger.info("_port_status_handler, dpid: %d, port added %s" %(dpid, port_no))
            self._addLocalPort(datapath, port)
        elif reason == ofproto.OFPPR_DELETE:
            self.logger.info("_port_status_handler, dpid: %d, port deleted %s" %(dpid, port_no))
            # self._ls(datapath.ports)
            # print(type(datapath.ports))
            # for key in datapath.ports.iterkeys():
            #     print(key)
            #     print(datapath.ports[key])
            self._delLocalPort(datapath, port)
        elif reason == ofproto.OFPPR_MODIFY:
            self.logger.info("_port_status_handler, dpid: %d, port modified %s" %(dpid, port_no))
        else:
            self.logger.info("_port_status_handler, dpid: %d, Illeagal port state %s %s" %(dpid, port_no, reason))

        self.logger.info('OFPPortStatus received: reason=%s desc=%s',
                            reason, msg.desc)

    @set_ev_cls(event.EventSwitchEnter)
    def _addSwitch(self,ev):
        switch = ev.switch
        # self._ls(switch)
        # self._ls(switch.ports)
        # print(switch.to_dict())
        # print(type(switch.ports))
        for port in switch.ports:
            # print(port)
            # self._ls(port)
            self._addLocalPort(switch.dp, port)
        self._peerPortTable[switch.dp.id] = {}

    @set_ev_cls(event.EventSwitchLeave)
    def _delSwitch(self,ev):
        switch = ev.switch
        del self._localPortTable[switch.dp.id]
        del self._peerPortTable[switch.dp.id]

    @set_ev_cls(event.EventLinkAdd)
    def _addLink(self,ev):
        link = ev.link
        # self._ls(link.dst)
        # print(link.dst)
        # print(type(link))
        # print(link)

        dstPort = link.dst
        dstDpid = dstPort.dpid
        dstDatapath = self.topoCollector.switches[dstDpid].dp
        self._addLocalPort(dstDatapath, dstPort)

        srcPort = link.src
        srcDpid = srcPort.dpid
        srcDatapath = self.topoCollector.switches[srcDpid].dp
        self._addLocalPort(srcDatapath, srcPort)

        self._addPeerPort(srcDatapath, link)

    @set_ev_cls(event.EventLinkDelete)
    def _delLink(self,ev):
        link = ev.link
        srcPort = link.src
        srcDpid = srcPort.dpid
        srcDatapath = self.topoCollector.switches[srcDpid].dp
        self._delPeerPort(srcDatapath, link)

    @set_ev_cls(event.EventHostAdd)
    def _addHost(self,ev):
        host = ev.host
        port = host.port
        dpid = port.dpid
        datapath = self.topoCollector.switches[dpid].dp
        self._addLocalPort(datapath, port)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                ev.msg.msg_len, ev.msg.total_len)

        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return  # ignore lldp packet

        dpid = datapath.id
        self.logger.debug("L2._packet_in_handler, dpid:%d, in_port:%d" %(dpid, in_port) )
        if eth.ethertype == ether_types.ETH_TYPE_ARP:
            self.logger.debug("get an arp")
            arpHeader = pkt.get_protocol(arp.arp)

            # Isolate broadcast domain
            self.logger.debug( "arpHeader.dst_ip:%s, net:%s"  %(arpHeader.dst_ip, self._getLANNet(datapath.id)) )
            lanNet = self._getLANNet(datapath.id)
            if (self._isLANIP(arpHeader.dst_ip, lanNet) and
                self._isLANIP(arpHeader.src_ip, lanNet)):
                self.logger.debug("This arp is from local LAN")

                # Self-learning bridge
                if not self._switchesLANMacTable[dpid].has_key(arpHeader.src_mac):
                    self._switchesLANMacTable[dpid][arpHeader.src_mac] = in_port
                    match = parser.OFPMatch(eth_dst=arpHeader.src_mac)
                    actions = [parser.OFPActionOutput(in_port)]
                    inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,actions)]
                    self._add_flow(datapath, match, inst, table_id=L2_TABLE, priority=1)

                if arpHeader.opcode == arp.ARP_REQUEST:
                    if arpHeader.dst_ip == self._getSwitchGatewayIP(datapath.id):
                        self.logger.debug("Arp request gateway's mac")
                        # If gateway: send arpReply to sender
                        in_port_info = self.dpset.get_port(datapath.id, in_port)
                        src_mac = in_port_info.hw_addr
                        self.logger.debug("Switch's arp reply, src_mac:%s", src_mac)
                        src_ip = arpHeader.dst_ip
                        dst_mac = arpHeader.src_mac
                        dst_ip = arpHeader.src_ip
                        data = self._build_arp(arp.ARP_REPLY,src_mac, src_ip, dst_mac, dst_ip)

                        out_port = in_port
                        actions = [parser.OFPActionOutput(out_port)]

                        out = parser.OFPPacketOut(
                            datapath=datapath, buffer_id=ofproto.OFP_NO_BUFFER, 
                            in_port=ofproto_v1_3.OFPP_CONTROLLER,
                            actions=actions, data=data)
                        datapath.send_msg(out)
                    else:
                        self.logger.debug("Arp request host's mac")
                        if arpHeader.dst_mac in self._switchesLANMacTable[dpid]:
                            out_port = self._switchesLANMacTable[dpid][arpHeader.dst_mac]
                        else:
                            out_port = ofproto.OFPP_FLOOD

                        out_port = ofproto.OFPP_FLOOD
                        actions = [parser.OFPActionOutput(out_port)]

                        data = None
                        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                            data = msg.data

                        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                                in_port=in_port, actions=actions, data=data)
                        datapath.send_msg(out)
                else:
                    self.logger.debug("Arp reply from host in LAN")
                    if arpHeader.dst_mac in self._switchesLANMacTable[dpid]:
                        out_port = self._switchesLANMacTable[dpid][arpHeader.dst_mac]

                    out_port = ofproto.OFPP_FLOOD
                    actions = [parser.OFPActionOutput(out_port)]

                    data = None
                    if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                        data = msg.data

                    out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                            in_port=in_port, actions=actions, data=data)
                    datapath.send_msg(out)
            else:
                self.logger.debug("This arp is from other LAN, drop it")