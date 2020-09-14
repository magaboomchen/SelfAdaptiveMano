#!/usr/bin/python
# -*- coding: UTF-8 -*-

import json

from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import arp, ipv4, icmp
from ryu.lib.packet import ether_types
from ruamel import yaml

from sam.ryu.conf.genSwitchConf import SwitchConf
from sam.ryu.conf.ryuConf import *
from sam.base.socketConverter import SocketConverter
from sam.base.messageAgent import *

class BaseApp(app_manager.RyuApp):
    def __init__(self, *args, **kwargs):
        super(BaseApp, self).__init__(*args, **kwargs)
        self._switchConfs = {}
        self._initSwitchConf(SWITCH_CONF_FILEPATH)
        self._messageAgent = MessageAgent()

    def _initSwitchConf(self,filepath):
        yamlObj = yaml.YAML()
        yamlObj.register_class(SwitchConf)
        with open(filepath) as f:
            content = yamlObj.load(f)
            self._switchConfs = content

    def _add_flow(self, datapath, match, instructions, table_id=0, priority = ofproto_v1_3.OFP_DEFAULT_PRIORITY):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        mod = parser.OFPFlowMod(
            datapath=datapath, match=match, cookie=0, cookie_mask=0, table_id = table_id,
            command=ofproto.OFPFC_ADD, idle_timeout=0, hard_timeout=0,
            priority=priority,flags=ofproto.OFPFF_SEND_FLOW_REM,
            instructions=instructions
        )
        datapath.send_msg(mod)

    def _del_flow(self, datapath, match, table_id=0, priority = ofproto_v1_3.OFP_DEFAULT_PRIORITY):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        mod = parser.OFPFlowMod(
            datapath=datapath, match=match, cookie=0, cookie_mask=0, table_id = table_id,
            command=ofproto.OFPFC_DELETE, idle_timeout=0, hard_timeout=0,
            priority=priority,flags=ofproto.OFPFF_SEND_FLOW_REM,
            out_port=ofproto.OFPP_ANY, out_group=ofproto.OFPG_ANY
        )
        datapath.send_msg(mod)

    def _clear_flow(self, datapath, table_id_list):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        empty_match = parser.OFPMatch()
        instructions = []
        for table_id in table_id_list:
            flow_mod = self._del_flow(datapath, empty_match, table_id)

    def _getLANNet(self,dpid):
        return self._switchConfs[dpid].lANNet

    # TODO: refactor, move this function to class SocketConverter()
    def _isLANIP(self, dstIP, net):
        dstIPNum = SocketConverter().ip2int(dstIP)

        netIP = net.split('/')[0]        
        netIPNum = SocketConverter().ip2int(netIP)

        netIPPrefixNum = int(net.split('/')[1])
        netIPMask = SocketConverter().ipPrefix2Mask(netIPPrefixNum)
        netIPMaskNum = SocketConverter().ip2int(netIPMask)

        return (dstIPNum & netIPMaskNum) == (netIPNum & netIPMaskNum)

    def _isDCNGateway(self,dpid):
        return self._switchConfs[dpid].switchType == "DCNGateway"

    def _build_arp(self, opcode, src_mac, src_ip, dst_mac, dst_ip):
        e = ethernet.ethernet(dst=dst_mac, src=src_mac, ethertype=ether_types.ETH_TYPE_ARP)
        a = arp.arp(hwtype=1, proto=ether_types.ETH_TYPE_IP, hlen=6, plen=4,
                    opcode=opcode, src_mac=src_mac, src_ip=src_ip,
                    dst_mac=dst_mac, dst_ip=dst_ip)
        p = packet.Packet()
        p.add_protocol(e)
        p.add_protocol(a)
        p.serialize()
        return p

    def _build_icmp_dest_unreach(self, src_mac, src_ip, dst_mac, dst_ip):
        e = ethernet.ethernet(dst=dst_mac, src=src_mac, ethertype=ether_types.ETH_TYPE_IP)
        ipv4Header = ipv4.ipv4(src=src_ip, dst=dst_ip)
        icmpHeader = icmp.dest_unreach()
        p = packet.Packet()
        p.add_protocol(e)
        p.add_protocol(ipv4Header)
        p.add_protocol(icmpHeader)
        p.serialize()
        return p

    def _getSwitchGatewayIP(self,dpid):
        return self._switchConfs[dpid].gatewayIP

    def _ls(self,obj):
        # Handy function that lists all attributes in the given object
        self.logger.info("list attributes of:{0}".format(type(obj)))
        self.logger.info("\n".join([x for x in dir(obj) if x[0] != "_"]))


    def _dict2OrderJson(self,dict):
        return json.dumps(dict, sort_keys=True)

    def _orderJson2dict(self,orderJson):
        return json.loads(orderJson)

    def _broadcastArpRequest(self,datapath,dstIP):
        ports = self.dpset.get_ports(datapath.id)
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        for port in ports:
            src_mac = port.hw_addr
            self.logger.debug("Send arp request, src_mac:%s", src_mac)
            src_ip = self._getSwitchGatewayIP(datapath.id)
            dst_mac = "FF:FF:FF:FF:FF:FF"
            data = self._build_arp(arp.ARP_REQUEST,src_mac, src_ip, dst_mac, dstIP)

            out_port = port.port_no
            actions = [parser.OFPActionOutput(out_port)]

            out = parser.OFPPacketOut(
                datapath=datapath, buffer_id=ofproto.OFP_NO_BUFFER, 
                in_port=ofproto_v1_3.OFPP_CONTROLLER,
                actions=actions, data=data)
            datapath.send_msg(out)
