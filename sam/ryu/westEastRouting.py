#!/usr/bin/python
# -*- coding: UTF-8 -*-

import copy

import networkx as nx
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.ofproto import ofproto_v1_4_parser
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv4
from ryu.lib.packet import arp
from ryu.lib.packet import ether_types
from ryu.controller import dpset
from ryu.base.app_manager import lookup_service_brick

from sam.ryu.conf.ryuConf import MAIN_TABLE
from sam.ryu.topoCollector import TopoCollector, TopologyChangeEvent
from sam.ryu.baseApp import BaseApp
from sam.base.loggerConfigurator import LoggerConfigurator


class WestEastRouting(BaseApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {
        'dpset': dpset.DPSet,
        'TopoCollector': TopoCollector
        }

    def __init__(self, *args, **kwargs):
        super(WestEastRouting, self).__init__(*args, **kwargs)
        self.dpset = kwargs['dpset']
        self.topoCollector = kwargs['TopoCollector']
        _EVENTS = [TopologyChangeEvent]

        self.L2 = lookup_service_brick('L2')

        self._westEastRIB = {}  # {dpid:{matchFields:inst,matchFields:inst}}, store current rib entry
        self._cacheWestEastRIB = {}  # store new tmp rib entry

        self._switchesLANArpTable = {}
        self._LANRIB = {}

        self._cacheSwitches = {}
        self._cacheLinks = {}
        self._cacheHosts = {}

        logConfigur = LoggerConfigurator(__name__, './log', 'westEastRouting.log', level='info')
        self.logger = logConfigur.getLogger()

    def getMacByIp(self,dpid,ipAddress):
        if self._switchesLANArpTable.has_key(dpid) and \
            self._switchesLANArpTable[dpid].has_key(ipAddress):
            return self._switchesLANArpTable[dpid][ipAddress]
        else:
            return None

    def _STSP(self,dpid):
        self.logger.debug("calculate stsp for dpid: %d" %dpid)

        # using networkx
        G = nx.DiGraph()
        for switch in self._cacheSwitches.iterkeys():
            self.logger.debug("Graph add switch: %d" %switch)
            G.add_node(switch)
        for link in self._cacheLinks.iterkeys():
            self.logger.debug("Graph add link: (%d,%d)" %(link[0], link[1]) )
            G.add_edge(link[0],link[1],weight=1)

        path = None
        if G.has_node(dpid):
            self.logger.debug("Target node: %d" %(dpid))
            self.logger.debug("Graph's nodes number: %d" %G.number_of_nodes())
            path = nx.single_target_shortest_path(G, dpid)
            self.logger.debug("path:")
            self.logger.debug(path)
        else:
            self.logger.warning("_STSP: No target node in graph")
        return path

    def _stsp2spt(self, stsPath):
        self.logger.info("start converting")
        spt = {}    # {dpid:nexthop}
        targetDPID = None
        for keys in stsPath.iterkeys():
            path = stsPath[keys]
            self.logger.debug("path:{0}".format(path))
            # self.logger.debug("typeOfPath:{0}".format(type(path)))
            targetDPID = path[-1]
            path.reverse()
            # self.logger.debug("typeOfPath:{0}".format(type(path)))
            for index in range(len(path)-1):
                dstDpid = path[index]
                srcDpid = path[index+1]
                if not spt.has_key(srcDpid):
                    spt[srcDpid] = dstDpid
                else:
                    self.logger.debug("Detect equal multi path, ignore it.")
        if spt == {}:
            return None
        else:
            return spt

    def _genATargeSwitchWestEastRIB(self,spt,targetDpid):
        self.logger.debug("_genATargeSwitchWestEastRIB")
        net = self._getLANNet(targetDpid)
        for srcDpid in spt.iterkeys():
            dstDpid = spt[srcDpid]
            self.logger.debug("srcDpid:%d -> dstDpid:%d" %(srcDpid,dstDpid))
            datapath = self._cacheSwitches[srcDpid].dp
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            matchFields={'eth_type':ether_types.ETH_TYPE_IP,'ipv4_dst':net}
            match = parser.OFPMatch(
                **matchFields
            )

            link = self._cacheLinks[srcDpid,dstDpid]
            out_port = link.src.port_no
            actions = [
                # parser.OFPActionDecNwTtl(),
                parser.OFPActionSetField(eth_src=link.src.hw_addr),
                parser.OFPActionSetField(eth_dst=link.dst.hw_addr),
                parser.OFPActionOutput(out_port)
            ]
            inst = [
                parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,actions),
                # parser.OFPInstructionGotoTable(table_id=L2_TABLE)
            ]

            if not self._cacheWestEastRIB.has_key(srcDpid):
                self._cacheWestEastRIB[srcDpid] = {}
            self._cacheWestEastRIB[srcDpid][self._dict2OrderJson(matchFields)] = inst

    def _updateAllSwitchWestEastRIB(self):
        westEastRIBTmp = copy.copy(self._westEastRIB)
        self.logger.debug("_updateAllSwitchWestEastRIB")

        for dpid in westEastRIBTmp.iterkeys():
            if not self._cacheWestEastRIB.has_key(dpid):
                self.logger.debug("old table set has this dpid && new table set dosen't hast this dpid")
                del self._westEastRIB[dpid]
 
        for dpid in self._cacheWestEastRIB.iterkeys():
            datapath = self._cacheSwitches[dpid].dp
            if not self._westEastRIB.has_key(dpid):
                self.logger.debug("old table set dosen't has this dpid && new tables set has this dpid")
                self._westEastRIB[dpid] = copy.deepcopy(self._cacheWestEastRIB[dpid])
                for matchFieldsJson in self._cacheWestEastRIB[dpid].iterkeys():
                    inst = self._cacheWestEastRIB[dpid][matchFieldsJson]
                    self.logger.debug("_updateAllSwitchWestEastRIB: Add_flow to dpid:%d" %(dpid) )
                    self.logger.debug("matchFieldsJson:", matchFieldsJson)
                    matchFields = self._orderJson2dict(matchFieldsJson)
                    match = ofproto_v1_4_parser.OFPMatch(
                        **matchFields
                    )
            else:
                self.logger.debug("old table set has this dpid && new tables set has this dpid")
                for matchFieldsJson in self._cacheWestEastRIB[dpid].iterkeys():
                    if self._westEastRIB[dpid].has_key(matchFieldsJson):
                        self.logger.debug("new entry is in old rib")
                        matchFields = self._orderJson2dict(matchFieldsJson)
                        match = ofproto_v1_4_parser.OFPMatch(
                            **matchFields
                        )
                    else:
                        self.logger.debug("new entry is not in old rib")
                    self._westEastRIB[dpid][matchFieldsJson] = self._cacheWestEastRIB[dpid][matchFieldsJson]
                    matchFields = self._orderJson2dict(matchFieldsJson)
                    match = ofproto_v1_4_parser.OFPMatch(
                        **matchFields
                    )
                    inst = self._cacheWestEastRIB[dpid][matchFieldsJson]

                westEastRIBofADpidTmp = copy.copy(self._westEastRIB[dpid])
                for matchFieldsJson in westEastRIBofADpidTmp.iterkeys():
                    if not self._cacheWestEastRIB[dpid].has_key(matchFieldsJson):
                        self.logger.debug("old entry doesn't existed in new rib")
                        del self._westEastRIB[dpid][matchFieldsJson]
                        self.logger.debug("_updateAllSwitchWestEastRIB: del_flow from dpid:%d" %(dpid) )
                        self.logger.debug(matchFieldsJson)
                        matchFields = self._orderJson2dict(matchFieldsJson)
                        match = ofproto_v1_4_parser.OFPMatch(
                            **matchFields
                        )

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _switchFeaturesHandler(self, ev):
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
        self._westEastRIB[datapath.id] = {}
        self._switchesLANArpTable[datapath.id] = {}

    @set_ev_cls(TopologyChangeEvent)
    def _topology_change_event_handler(self, ev):
        self.logger.info('*** WestEastRouting Received topology change event')

        # copy topoLearner's topology: avoid topology change when calculating STSP
        self._cacheSwitches = copy.copy(self.topoCollector.switches)
        self._cacheLinks = copy.copy(self.topoCollector.links)
        self._cacheHosts = copy.copy(self.topoCollector.hosts)

        self._cacheWestEastRIB = {}
        for dpid in self.topoCollector.switches.iterkeys():
            self.logger.debug("Update Single Target Shortest Path start.")
            stsPath = self._STSP(dpid)
            if stsPath == None:
                self.logger.warning("Update Single Target Shortest Path failed.")
                continue
            spt = self._stsp2spt(stsPath)
            if spt == None:
                self.logger.warning("Convert Single Target Shortest Path to Shortest Path Tree failed.")
                continue
            self._genATargeSwitchWestEastRIB(spt, dpid)
        # self._updateAllSwitchWestEastRIB()

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
        in_port = msg.match['in_port']  # inport number
        in_port_info = self.dpset.get_port(datapath.id, in_port)

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return  # ignore lldp packet

        dpid = datapath.id
        self.logger.debug("westEastRouting._packet_in_handler, dpid:%d, in_port:%d" %(dpid, in_port) )

        if msg.table_id == MAIN_TABLE:
            if eth.ethertype == ether_types.ETH_TYPE_IP:
                ipHeader = pkt.get_protocol(ipv4.ipv4)
                self.logger.info("WestEast app get an IPv4 packet, dst ip:%s" %(ipHeader.dst))
                if self._isLANIP(ipHeader.dst, self._getLANNet(datapath.id)):
                    # If dst is local host: send arp request to all port
                    ports = self.dpset.get_ports(datapath.id)
                    for port in ports:
                        src_mac = port.hw_addr
                        self.logger.info("Send arp request, src_mac:%s", src_mac)
                        src_ip = self._getSwitchGatewayIP(datapath.id)
                        dst_mac = "FF:FF:FF:FF:FF:FF"
                        dst_ip = ipHeader.dst
                        data = self._build_arp(arp.ARP_REQUEST, src_mac, src_ip, dst_mac, dst_ip)

                        out_port = port.port_no
                        actions = [parser.OFPActionOutput(out_port)]

                        out = parser.OFPPacketOut(
                            datapath=datapath, buffer_id=ofproto.OFP_NO_BUFFER, 
                            in_port=ofproto_v1_3.OFPP_CONTROLLER,
                            actions=actions, data=data)
                        datapath.send_msg(out)
            elif eth.ethertype == ether_types.ETH_TYPE_ARP:
                self.logger.debug("WestEast app get an arp frame")
                arpHeader = pkt.get_protocol(arp.arp)

                # Isolate broadcast domain
                if self._isLANIP(arpHeader.dst_ip, self._getLANNet(datapath.id)):
                    mac = arpHeader.src_mac
                    srcIP = arpHeader.src_ip

                    # Self-learning bridge
                    if not self._switchesLANArpTable[dpid].has_key(srcIP):
                        self._switchesLANArpTable[dpid][srcIP] = mac

                        ofproto = datapath.ofproto
                        parser = datapath.ofproto_parser
                        matchFields={'eth_type':ether_types.ETH_TYPE_IP,'ipv4_dst':srcIP }
                        match = parser.OFPMatch(
                            **matchFields
                        )

                        actions = [
                            parser.OFPActionSetField(eth_src=in_port_info.hw_addr),
                            parser.OFPActionSetField(eth_dst=mac),
                            parser.OFPActionOutput(in_port)
                        ]
                        inst = [
                            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,actions),
                        ]

                        self.logger.debug("_packet_in_handler: Add_flow")
                        self._add_flow(datapath, match, inst, table_id=MAIN_TABLE, priority=2)
                        self._LANRIB[self._dict2OrderJson(matchFields)] = inst