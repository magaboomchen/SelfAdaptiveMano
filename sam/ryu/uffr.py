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
from sam.base.socketConverter import *

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

    def __init__(self, *args, **kwargs):
        super(UFFR, self).__init__(*args, **kwargs)
        self.logger.info("Initialize UFFR App !")
        self.dpset = kwargs['dpset']
        self.topoCollector = kwargs['TopoCollector']
        self.L2 = lookup_service_brick('L2')
        self.wer = lookup_service_brick('WestEastRouting')
        if self.L2 == None or self.wer == None:
            self.logger.error("UFFR service connection error. You may need to sort app's start sequence")
            return 
        self.uibm = UIBMaintainer()
        self._sc = SocketConverter()
        self.logger.setLevel(logging.DEBUG)
        self.logger.info("UFFR App is running !")





    def _addSfciHandler(self, cmd):
        self.logger.debug('*** UFFR App Received command= %s', cmd)
        sfc = cmd.attributes['sfc']
        sfci = cmd.attributes['sfci']
        self._addRoute2Classifier(sfc,sfci)
        self._addSFCIRoute(sfc,sfci)
        self._sendCmdRply(cmd.cmdID,CMD_STATE_SUCCESSFUL)

    def _addRoute2Classifier(self,sfc,sfci):
        # install route to classifier
        for direction in sfc.directions:
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

    def _getFirstSwitchIDInSFCI(self,sfci,direction):
        FPSet = sfci.ForwardingPathSet
        directionID = direction["ID"]
        if directionID == 0:
            firstPath = FPSet.primaryForwardingPath[DIRECTION1_PATHID_OFFSET]
        else:
            firstPath = FPSet.primaryForwardingPath[DIRECTION2_PATHID_OFFSET]
        firstSwitchID = firstPath[1]    # the first node is a server, the second node is a switch
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
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
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



    def _addSFCIRoute(self,sfc,sfci):
        # install sfci path
        for direction in sfc.directions:
            # install primary path route
            self._installPrimaryPath(sfci,direction)
            # install backup paths route
            self._installBackupPaths(sfci,direction)

    def _installPrimaryPath(self,sfci,direction):
        primaryFP = self._getPrimaryPath(sfci,direction["ID"])
        stageCount = -1
        for stage in primaryFP:
            stageCount = stageCount + 1
            if len(stage)==2:
                # SFF inner routing
                continue
            (srcServerID,dstServerID) = self._popSrcDstServerInStage(stage)
            # add route between switches
            for i in range(len(stage)-1):
                currentSwitchID = stage[i]
                nextSwitchID = stage[i+1]
                dstIP = self.getUFFRDstIP(SFCIID,stageCount,
                    DIRECTION1_PATHID_OFFSET)
                groupID = self.uibm.assignGroupID(currentSwitchID)
                self._addUFFRSFCIFlowtable(currentSwitchID,sfci.SFCIID,dstIP,
                    groupID)
                self._addUFFRSFCIGroupTable(currentSwitchID,sfci.SFCIID,dstIP,
                    groupID)
            # add route between switch and server
            lastSwitchID = stage[-1]
            # TODO

    def _getPrimaryPath(self,sfci,directionID):
        if directionID == 0:
            pathID = DIRECTION1_PATHID_OFFSET
        else:
            pathID = DIRECTION2_PATHID_OFFSET
        primaryFP = sfci.ForwardingPathSet.primaryForwardingPath[pathID]
        return primaryFP

    def _popSrcDstServerInStage(self,stage):
        srcServerID = stage[0]
        dstServerID = stage[-1]
        del stage[0]    # serverID
        del stage[-1]   # serverID
        return (srcServerID,dstServerID)

    def _addUFFRSFCIFlowtable(self,currentSwitchID,SFCIID,dstIP,groupID)
        datapath = self.dpset.get(int(str(currentSwitchID),0))
        matchFields = {'eth_type':ether_types.ETH_TYPE_IP,
            'ipv4_dst':dstIP}
        match = parser.OFPMatch(
            **matchFields
        )
        actions = [
            parser.OFPActionGroup(groupID)
        ]
        inst = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,actions)
        ]
        self._add_flow(datapath, match, inst, table_id=UFFR_TABLE,
            priority = 1)
        self.uibm.addSFCIFlowTableEntry(sfci.SFCIID,currentSwitchID,
            matchFields,groupID)

    def getUFFRDstIP(self,sfci,stageCount,pathID):
        sfcID = sfci.SFCIID
        vmfID = sfci.VNFISequence[stageCount][0].VNFID
        ipNum = (10<<24) + ((sfcID & 0xFFF) << 12) + ((vnfID & 0xF) << 8) \
            + (pathID & 0xFF)
        return self._sc.int2ip(ipNum)

    def _addUFFRSFCIGroupTable(currentSwitchID,SFCIID,dstIP,groupID):
        pass
        # TODO

    def _installBackupPaths(self,sfci,direction):
        pass




    def _delSfciHandler(self, cmd):
        self.logger.debug('*** UFFR App Received command= %s', cmd)
        sfc = cmd.attributes['sfc']
        sfci = cmd.attributes['sfci']
        self._delRoute2Classifier(sfc,sfci)
        self._delSFCIRoute(sfc,sfci)
        self._sendCmdRply(cmd.cmdID,CMD_STATE_SUCCESSFUL)

    def _delRoute2Classifier(self,sfc,sfci):
        # TODO
        pass

    def _delSFCIRoute(self,sfc,sfci):
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

    def _sendCmdRply(self,cmdID,cmdState):
        cmdRply = CommandReply(cmdID,cmdState)
        self._cmdReplyHandler(cmdRply)

    def _cmdReplyHandler(self, cmdRply):
        print("RyuCommandAgent get a cmdRply !")
        rplyMsg = SAMMessage(MSG_TYPE_NETWORK_CONTROLLER_CMD_REPLY,cmdRply)
        queue = MEDIATOR_QUEUE
        self._messageAgent.sendMsg(queue,rplyMsg)