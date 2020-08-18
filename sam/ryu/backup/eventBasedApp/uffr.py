from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.controller import dpset
from ryu.controller import event
from ryu.ofproto import ofproto_v1_3
from ryu.ofproto import ofproto_v1_3_parser
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv4
from ryu.lib.packet import arp
from ryu.lib.packet import ether_types
from ryu.topology import switches
from ryu.base.app_manager import *

from sam.ryu.conf.ryuConf import *
from sam.ryu.conf.genSwitchConf import SwitchConf
from sam.ryu.topoCollector import TopoCollector, TopologyChangeEvent
from sam.ryu.baseApp import BaseApp
from sam.ryu.ryuCommandAgent import *
from sam.ryu.uibMaintainer import *
from sam.base.messageAgent import *
from sam.base.command import *
from sam.base.path import *

import logging
import networkx as nx
import copy
import time

class UFFR(BaseApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {
        'dpset': dpset.DPSet,
        'TopoCollector': TopoCollector
        }
    _EVENTS = [AddSfciEvent,DelSfciEvent]

    def __init__(self, *args, **kwargs):
        super(UFFR, self).__init__(*args, **kwargs)
        print("Initialize UFFR App !")
        self.dpset = kwargs['dpset']
        self.topoCollector = kwargs['TopoCollector']
        self.L2 = lookup_service_brick('L2')
        self.wer = lookup_service_brick('WestEastRouting')
        self.rca = lookup_service_brick('RyuCommandAgent')
        self.uibm = UIBMaintainer()
        self.logger.setLevel(logging.DEBUG)
        print("UFFR App is running !")

    def _sendCmdRply(self,cmdID,cmdState):
        cmdRply = CommandReply(cmdID,cmdState)
        self.rca._cmdReplyHandler(cmdRply)

    @set_ev_cls(AddSfciEvent)
    def _addSfciEventHandler(self, ev):
        print('*** UFFR App Received event: ev.msg = %s', ev.msg)
        cmd = ev.msg
        sfc = cmd['sfc']
        sfci = cmd['sfci']
        # install route to classifier
        for directioin in sfc.directions:
            dpid = self._getFirstSwitchIDInSFCI(sfci,direction)
            datapath = self.dpset.get(int(str(dpid), 0))
            source = direction['source']
            if source == None:
                inPortNum = DCNGATEWAY_INBOUND_PORT
            elif source.has_key("IPv4"):
                inPortNum = self._getPortbyIP(datapath,source["IPv4"])
                if inPortNum == None:
                    self._sendCmdRply(cmd.cmdID,CMD_STATE_FAIL)
            else:
                self._sendCmdRply(cmd.cmdID,CMD_STATE_FAIL)
            classifierMAC = direction['ingress'].getDatapathNICMac()
            self._installRoute4Switch2Classifier(
                datapath,inPortNum,classifierMAC)

        # install sfci
        pathSet = sfci.ForwardingPathSet
        for path in pathSet:
            ribs = self._genRibs(path,sfc,sfci)
            self._addRibs(ribs)
            self._installFibs(ribs)
        self._sendCmdRply(cmd.cmdID,CMD_STATE_SUCCESSFUL)

    def _getFirstSwitchIDInSFCI(self,sfci,direction):
        FPset = sfci.ForwardingPathSet
        directionID = direction["ID"]
        if directionID == 0:
            firstPath = FPset.primaryForwardingPath[DIRECTION1_PATHID_OFFSET]
        else:
            firstPath = FPset.primaryForwardingPath[DIRECTION2_PATHID_OFFSET]
        firstSwitchID = firstPath[0][1]
        return firstSwitchID
    
    # group table set dst port design:
    # uffr.py use event to request mac-port mapping from _switchesLANMacTable in L2.py.
    # in L2.py, check _switchesLANMacTable, if it unexisted, return None, and send arp request.
    # if uffr get None, time.sleep(0.25) then retry again, max try number is 4.
    def _getPortbyIP(self,datapath,ipAddress):
        dpid = datapath.id
        maxTryNumber = 4
        port = None
        for tryNumber in range(maxTryNumber):
            # get mac by arp table
            dstMac = self.wer.getMacByIp(dpid,ipAddress)
            if dstMac == None:
                self._broadcastArpRequest(datapath,dstIP)
                time.sleep(0.25)
                continue

            # get port by mac table
            port = self.getPortByMac(dpid,dstMac)
            if port == None:
                continue
        return port

    def _installRoute4Switch2Classifier(self,datapath,inPortNum,classifierMAC):
        dpid = datapath.id
        match = parser.OFPMatch(
            in_port=inPortNum, eth_type=ether_types.ETH_TYPE_IP
        )
        in_port_info = self.dpset.get_port(dpid, inPortNum)
        actions = [
            parser.OFPActionDecNwTtl(),
            parser.OFPActionSetField(eth_src=in_port_info.hw_addr),
            parser.OFPActionSetField(eth_dst=classifierMAC)
        ]
        inst = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,actions),
            parser.OFPInstructionGotoTable(table_id=L2_TABLE)
        ]
        self._add_flow(datapath,match,inst,table_id=IPv4_CLASSIFIER_TABLE, priority=3)

    def _broadcastArpRequest(self,datapath,dstIP):
        ports = self.dpset.get_ports(datapath.id)
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

    def _genRibs(self,path,sfc,sfci):
        pass

    def _addRibs(self,ribs):
        pass

    def _installFibs(self,ribs):
        pass

    @set_ev_cls(DelSfciEvent)
    def _delSfciEventHandler(self, ev):
        cmd = ev.msg
        sfc = cmd['sfc']
        sfci = cmd['sfci']
        # uninstall route to classifier

        # uninstall sfci
        SFCIID = sfci.SFCIID
        self._uninstallFibs(SFCIID)
        self._delRibs(SFCIID)

    def _uninstallFibs(self,SFCIID):
        # TODO
        pass

    def _delRibs(self,SFCIID):
        # TODO
        pass

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _switchFeaturesHandler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id

        # install table-miss flow entry in UFFR_TABLE
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        self._add_flow(datapath, match, inst, table_id = UFFR_TABLE, priority=0)

        # initial IPv4_CLASSIFIER_TABLE
        match = parser.OFPMatch(
            eth_type=ether_types.ETH_TYPE_IP,ipv4_dst="10.0.0.0/8"
        )
        inst = [parser.OFPInstructionGotoTable(table_id = UFFR_TABLE)]
        self._add_flow(datapath, match, inst, table_id = IPv4_CLASSIFIER_TABLE, priority=2)