#!/usr/bin/python
# -*- coding: UTF-8 -*-

import copy

from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import arp
from ryu.lib.packet import ether_types 
from ryu.controller import dpset
import networkx as nx

from sam.ryu.conf.ryuConf import MAIN_TABLE, DCN_GATEWAY_PEER_ARP, \
    DEFAULT_DCN_GATEWAY_PEER_SWITCH_MAC, DEFAULT_DCN_GATEWAY_OUTBOUND_PORT_NUMBER
from sam.ryu.topoCollector import TopoCollector, TopologyChangeEvent
from sam.ryu.baseApp import BaseApp
from sam.base.loggerConfigurator import LoggerConfigurator


class NorthSouthRouting(BaseApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {
        'dpset': dpset.DPSet,
        'TopoCollector': TopoCollector
        }

    def __init__(self, *args, **kwargs):
        super(NorthSouthRouting, self).__init__(*args, **kwargs)
        self.dpset = kwargs['dpset']
        self.topoCollector = kwargs['TopoCollector']
        _EVENTS = [TopologyChangeEvent]

        self._northSouthRIB = {}    # {dpid:{matchField:inst,matchField:inst}}
        self._cacheNorthSouthRIB = {}

        self._cacheSwitches = {}
        self._cacheLinks = {}
        self._cacheHosts = {}

        self._dcnGateways = []  # [dpid]
        self._defaultDCNGateway = None
        self._defaultDCNGatewayPeerSwitchMac = None

        logConfigur = LoggerConfigurator(__name__, './log', 'northSouthRouting.log', level='warning')
        self.logger = logConfigur.getLogger()

    def _STSP(self,dpid):
        self.logger.debug("calculate stsp for dpid: %d" %dpid)

        # using networkx
        G = nx.DiGraph()
        for switch in self._cacheSwitches.keys():
            self.logger.debug("Graph add switch: %d" %switch)
            G.add_node(switch)
        for link in self._cacheLinks.keys():
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
        for keys in stsPath.keys():
            path = stsPath[keys]
            self.logger.debug(path)
            # self.logger.debug(type(path))
            targetDPID = path[-1]
            path.reverse()
            # self.logger.debug(type(path))
            for index in range(len(path)-1):
                dstDpid = path[index]
                srcDpid = path[index+1]
                if not (srcDpid in spt):
                    spt[srcDpid] = dstDpid
                else:
                    self.logger.debug("Detect equal multi path, ignore it.")
        if spt == {}:
            return None
        else:
            return spt

    @set_ev_cls(TopologyChangeEvent)
    def _topology_change_event_handler(self, ev):
        self.logger.info('*** NorthSouthRouting Received topology change event')

        # copy topoLearner's topology: avoid topology change when calculating STSP
        self._cacheSwitches = copy.copy(self.topoCollector.switches)
        self._cacheLinks = copy.copy(self.topoCollector.links)
        self._cacheHosts = copy.copy(self.topoCollector.hosts)

        self._cacheNorthSouthRIB = {}
        self._updateDefaultDCNGateway()
        if len(self._dcnGateways)>0 and self._defaultDCNGateway!= None:
            dpid = self._defaultDCNGateway
            self.logger.debug("Update Single Target Shortest Path start.")
            stsPath = self._STSP(dpid)
            if stsPath == None:
                self.logger.warning("Update Single Target Shortest Path failed.")
                return 
            spt = self._stsp2spt(stsPath)
            if spt == None:
                self.logger.warning("Convert Single Target Shortest Path to Shortest Path Tree failed.")
                return 
            self._genASwitchNorthSouthRIB(spt, dpid)
        else:
            self.logger.warning("DCN Gateways totally down.")

        if DCN_GATEWAY_PEER_ARP == "STATIC" and self._defaultDCNGateway != None:
            self._defaultDCNGatewayPeerSwitchMac = DEFAULT_DCN_GATEWAY_PEER_SWITCH_MAC
            self._genDCNGatewaySouthRIB()

    def _updateDefaultDCNGateway(self):
        self.logger.debug("_updateDefaultDCNGateway")
        self._dcnGateways = []
        for dpid in self._cacheSwitches.keys():
            self.logger.debug("dpid: {0}".format(dpid))
            if self._isDCNGateway(dpid):
                self._dcnGateways.append(dpid)
        if not self._defaultDCNGateway in self._dcnGateways:
            if len(self._dcnGateways)>0:
                self.logger.debug("start update Default DCN Gateway")
                self._defaultDCNGateway = self._dcnGateways[0]
                self._defaultDCNGatewayPeerSwitchMac = None
                self._setDefaultDCNGatewayPeerSwitchMac()
            else:
                self._defaultDCNGateway = None
        else:
            # it should do nothing, but we have to trigger the update of rib
            self._setDefaultDCNGatewayPeerSwitchMac()

    def _setDefaultDCNGatewayPeerSwitchMac(self):
        # send arp request
        datapath = self.topoCollector.switches[self._defaultDCNGateway].dp
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        outPort = self.dpset.get_port(self._defaultDCNGateway, DEFAULT_DCN_GATEWAY_OUTBOUND_PORT_NUMBER)
        src_mac = outPort.hw_addr
        self.logger.debug("_setDefaultDCNGatewayPeerSwitchMac, Send arp request, src_mac:%s", src_mac)
        src_ip = self._switchConfs[self._defaultDCNGateway].dcnGatewaySelfIP
        dst_mac = "FF:FF:FF:FF:FF:FF"
        dst_ip = self._switchConfs[self._defaultDCNGateway].dcnGatewayPeerIP
        data = self._build_arp(arp.ARP_REQUEST,src_mac, src_ip, dst_mac, dst_ip)

        out_port = DEFAULT_DCN_GATEWAY_OUTBOUND_PORT_NUMBER
        actions = [parser.OFPActionOutput(out_port)]

        out = parser.OFPPacketOut(
            datapath=datapath, buffer_id=ofproto.OFP_NO_BUFFER, 
            in_port=ofproto_v1_3.OFPP_CONTROLLER,
            actions=actions, data=data)
        datapath.send_msg(out)

    def _genASwitchNorthSouthRIB(self,spt,targetDpid):
        self.logger.info("_genASwitchNorthSouthRIB")
        net = self._getLANNet(targetDpid)
        for srcDpid in spt.keys():
            dstDpid = spt[srcDpid]
            self.logger.debug("srcDpid:%d -> dstDpid:%d" %(srcDpid,dstDpid))
            datapath = self._cacheSwitches[srcDpid].dp
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            matchFields = {'eth_type':ether_types.ETH_TYPE_IP}
            match = parser.OFPMatch(
                **matchFields
            )

            link = self._cacheLinks[(srcDpid,dstDpid)]
            out_port = link.src.port_no

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

        self._northSouthRIB[datapath.id] = {}
        self.logger.warning("switch add dpid:{0}".format(datapath.id))

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
        # self.logger.debug("northSouthRouting._packet_in_handler, dpid:%d, in_port:%d" %(dpid, in_port) )

        if dpid == self._defaultDCNGateway and msg.table_id == MAIN_TABLE and eth.ethertype == ether_types.ETH_TYPE_ARP:
            # self.logger.debug("Get an arp packet in from default DCN gateway dpid: %d's MAIN table, packet type: %d" %(dpid, eth.ethertype))
            arpHeader = pkt.get_protocol(arp.arp)

            if (in_port == DEFAULT_DCN_GATEWAY_OUTBOUND_PORT_NUMBER
                    and arpHeader.opcode == arp.ARP_REPLY
                    and self._defaultDCNGateway != None
                    and arpHeader.src_ip == self._switchConfs[self._defaultDCNGateway].dcnGatewayPeerIP):
                self.logger.debug("dcn gateway peer switch's arp reply")
                # self.logger.warning("from dpid: {0} get a arp: {1}".format(datapath.id, pkt))

                if DCN_GATEWAY_PEER_ARP == "DYNAMIC":
                    self._defaultDCNGatewayPeerSwitchMac = arpHeader.src_mac
                    self._genDCNGatewaySouthRIB()

                # self._updateAllSwitchNorthSouthRIB()

            # if (in_port == DEFAULT_DCN_GATEWAY_OUTBOUND_PORT_NUMBER and arpHeader.opcode == arp.ARP_REPLY):
            #     self.logger.debug("DEBUG: dcn gateway peer switch's arp reply")
            #     self.logger.warning("DEBUG: from dpid: {0} get a arp: {1}".format(datapath.id, pkt))

        if dpid == self._defaultDCNGateway and eth.ethertype == ether_types.ETH_TYPE_ARP:
            arpHeader = pkt.get_protocol(arp.arp)
            if (arpHeader.opcode == arp.ARP_REQUEST
                    and arpHeader.dst_ip == self._switchConfs[self._defaultDCNGateway].dcnGatewaySelfIP):
                self.logger.debug("DCN gateway get an arp request: requeset DCN gateway's mac")
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

    def _genDCNGatewaySouthRIB(self):
        self.logger.debug("_genDCNGatewaySouthRIB")
        srcDpid = self._defaultDCNGateway
        datapath = self._cacheSwitches[srcDpid].dp
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        matchFields = {'eth_type':ether_types.ETH_TYPE_IP}
        match = parser.OFPMatch(**matchFields)

        outPort = self.dpset.get_port(self._defaultDCNGateway, DEFAULT_DCN_GATEWAY_OUTBOUND_PORT_NUMBER)
        srcMac = outPort.hw_addr
        dstMac = self._defaultDCNGatewayPeerSwitchMac
        actions = [
            parser.OFPActionSetField(eth_src=srcMac),
            parser.OFPActionSetField(eth_dst=dstMac),
            parser.OFPActionOutput(DEFAULT_DCN_GATEWAY_OUTBOUND_PORT_NUMBER)
        ]
        inst = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)
        ]

        if (srcDpid in self._cacheNorthSouthRIB.keys()
                and self._dict2OrderJson(matchFields) in self._cacheNorthSouthRIB[srcDpid]):
            return 

        if not (srcDpid in self._cacheNorthSouthRIB):
            self._cacheNorthSouthRIB[srcDpid] = {}
        self._cacheNorthSouthRIB[srcDpid][self._dict2OrderJson(matchFields)] = inst
        self.logger.debug(self._cacheNorthSouthRIB[srcDpid])

        self._add_flow(datapath, match, inst, table_id=MAIN_TABLE, priority=1)

    def _updateAllSwitchNorthSouthRIB(self):
        northSouthRIBTmp = copy.copy(self._northSouthRIB)
        self.logger.debug("_updateAllSwitchNorthSouthRIB")

        for dpid in northSouthRIBTmp.keys():
            if not (dpid in self._cacheNorthSouthRIB):
                self.logger.debug("old table set has this dpid && new table set dosen't hast this dpid")
                del self._northSouthRIB[dpid]

        for dpid in self._cacheNorthSouthRIB.keys():
            datapath = self._cacheSwitches[dpid].dp
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            if not (dpid in self._northSouthRIB):
                self.logger.debug("old table set dosen't has this dpid && new tables set has this dpid")
                self._northSouthRIB[dpid] = copy.deepcopy(self._cacheNorthSouthRIB[dpid])
                for matchFieldsJson in self._cacheNorthSouthRIB[dpid].keys():
                    inst = self._cacheNorthSouthRIB[dpid][matchFieldsJson]
                    self.logger.debug("_updateAllSwitchNorthSouthRIB: Add_flow to dpid:%d" %(dpid) )
                    self.logger.debug("matchFieldsJson:")
                    self.logger.debug(matchFieldsJson)
                    matchFields = self._orderJson2dict(matchFieldsJson)
                    match = parser.OFPMatch(
                        **matchFields
                    )
            else:
                self.logger.debug("old table set has this dpid && new tables set has this dpid")
                for matchFieldsJson in self._cacheNorthSouthRIB[dpid].keys():
                    if matchFieldsJson in self._northSouthRIB[dpid]:
                        self.logger.debug("new entry is in old rib")
                        matchFields = self._orderJson2dict(matchFieldsJson)
                        match = parser.OFPMatch(
                            **matchFields
                        )
                    else:
                        self.logger.debug("new entry is not in old rib")

                    self.logger.debug("update new entry into old entry")
                    self._northSouthRIB[dpid][matchFieldsJson] = copy.deepcopy(self._cacheNorthSouthRIB[dpid][matchFieldsJson])
                    matchFields = self._orderJson2dict(matchFieldsJson)
                    match = parser.OFPMatch(
                        **matchFields
                    )
                    inst = self._cacheNorthSouthRIB[dpid][matchFieldsJson]

                northSouthRIBofADpidTmp = copy.copy(self._northSouthRIB[dpid])
                for matchFieldsJson in northSouthRIBofADpidTmp.keys():
                    if not (matchFieldsJson in self._cacheNorthSouthRIB[dpid]):
                        self.logger.debug("old entry doesn't existed in new rib")
                        del self._northSouthRIB[dpid][matchFieldsJson]
                        self.logger.debug("_updateAllSwitchNorthSouthRIB: del_flow from dpid:%d" %(dpid) )
                        self.logger.debug(matchFieldsJson)
                        matchFields = self._orderJson2dict(matchFieldsJson)
                        match = parser.OFPMatch(
                            **matchFields
                        )
