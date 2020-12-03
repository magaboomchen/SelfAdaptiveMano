#!/usr/bin/python
# -*- coding: UTF-8 -*-

import copy
import time

from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.controller import dpset
from ryu.controller import event
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ipv4
from ryu.lib.packet import arp
from ryu.lib.packet import ether_types
from ryu.topology import switches
from ryu.base.app_manager import *

from sam.ryu.conf.ryuConf import *
from sam.ryu.topoCollector import TopoCollector, TopologyChangeEvent
from sam.ryu.baseApp import BaseApp
from sam.ryu.conf.ryuConf import *
from sam.ryu.nibMaintainer import NIBMaintainer
from sam.ryu.frr import FRR
from sam.base.messageAgent import *
from sam.base.command import *
from sam.base.path import *
from sam.base.socketConverter import *
from sam.base.vnf import *
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.serverController.serverManager.serverManager import *


class NotVia(FRR):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {
        'dpset': dpset.DPSet,
        'TopoCollector': TopoCollector
        }

    def __init__(self, *args, **kwargs):
        super(NotVia, self).__init__(*args, **kwargs)
        self.logger.info("Initialize NotVia App !")
        self.ibm = NIBMaintainer()
        self.logger.info("NotVia App is running !")

    def _addSFCHandler(self, cmd):
        self.logger.debug('*** NotVia App Received command= %s', cmd)
        try:
            sfc = cmd.attributes['sfc']
            self._addRoute2Classifier(sfc)
            self._sendCmdRply(cmd.cmdID,CMD_STATE_SUCCESSFUL)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                "Ryu app NotVia _addSFCHandler ")
            self._sendCmdRply(cmd.cmdID,CMD_STATE_FAIL)


    def _addSFCIHandler(self, cmd):
        self.logger.debug('*** NotVia App Received command= %s', cmd)
        try:
            sfc = cmd.attributes['sfc']
            sfci = cmd.attributes['sfci']
            self._addSFCIRoute(sfc,sfci)
            self._sendCmdRply(cmd.cmdID,CMD_STATE_SUCCESSFUL)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                "Ryu app NotVia _addSFCIHandler ")
            self._sendCmdRply(cmd.cmdID,CMD_STATE_FAIL)

    def _addSFCIRoute(self, sfc, sfci):
        # install sfci path
        for direction in sfc.directions:
            # install primary path route
            self._installPrimaryPath(sfci,direction)
            # install backup paths route
            self._installBackupPaths(sfci,direction)
        return True

    def _installPrimaryPath(self, sfci, direction):
        primaryPathID = self._getPathID(direction["ID"])
        primaryFP = self._getPrimaryPath(sfci,primaryPathID)
        stageCount = -1
        for stage in primaryFP:
            stageCount = stageCount + 1
            if len(stage)==2:
                # SFF inner routing
                continue
            dstIP = self.getSFCIStageDstIP(sfci, stageCount, primaryPathID)
            (srcServerID,dstServerID) = self._getSrcDstServerInStage(stage)
            # add route
            for i in range(1,len(stage)-1):
                currentSwitchID = stage[i]
                groupID = self.ibm.assignGroupID(currentSwitchID)
                self.logger.debug("dpid:{0}".format(currentSwitchID))
                self.logger.debug("______: assignGroupID:{0}".format(groupID))
                nextNodeID = stage[i+1]

                if self._canSkipPrimaryPathFlowInstallation(sfci.SFCIID,
                    dstIP, currentSwitchID):
                    continue

                self._addNotViaSFCIGroupTable(currentSwitchID,
                    nextNodeID, sfci, direction, stageCount, groupID)
                self._addNotViaSFCIFlowtable(currentSwitchID,
                    sfci.SFCIID, dstIP, groupID)

    def _addNotViaSFCIGroupTable(self, currentDpid, nextDpid, sfci, direction,
            stageCount, groupID):
        datapath = self.dpset.get(int(str(currentDpid),0))
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        buckets = []
        # get default src/dst ether and default OutPort
        (srcMAC,dstMAC,defaultOutPort) = self._getNextHopActionFields(sfci,
            direction,currentDpid,nextDpid)
        if defaultOutPort == None:
            raise ValueError("NotVia: can not get default out port")
        self.logger.debug("Bucket1")
        self.logger.debug("srcMAC:{0},dstMAC:{1},outport:{2}".format(srcMAC,dstMAC,
            defaultOutPort))
        actions = [
            parser.OFPActionDecNwTtl(),
            parser.OFPActionSetField(eth_src=srcMAC),
            parser.OFPActionSetField(eth_dst=dstMAC),
            parser.OFPActionOutput(defaultOutPort)
        ]
        watch_port = defaultOutPort
        bucket = parser.OFPBucket(watch_port=watch_port,actions=actions)
        buckets.append(bucket)

        # get backup src/dst ether, backup OutPort and new vlanID
        backupnextDpid = self._getBackupNextHop(currentDpid,nextDpid,sfci,
            direction,stageCount)
        self.logger.debug("backupnextDpid:{0}".format(backupnextDpid))
        if backupnextDpid != None:
            vlanID = self._getNewVLANID(currentDpid,nextDpid,sfci,direction)
            (srcMAC,dstMAC,backupOutPort) = self._getNextHopActionFields(sfci,
                direction,currentDpid,backupnextDpid)

            self.logger.debug("Bucket2")
            self.logger.debug("srcMAC:{0}, dstMAC:{1}, vlanID:{2}, outport:{2}".format(
                    srcMAC,dstMAC,vlanID,backupOutPort))
            actions = [
                parser.OFPActionDecNwTtl(),
                parser.OFPActionSetField(eth_src=srcMAC),
                parser.OFPActionSetField(eth_dst=dstMAC),
                parser.OFPActionPushVlan(ether_types.ETH_TYPE_8021Q),
                parser.OFPActionSetField(vlan_vid=vlanID),
                parser.OFPActionOutput(backupOutPort)
            ]
            watch_port = backupOutPort
            bucket = parser.OFPBucket(watch_port=watch_port,actions=actions)
            buckets.append(bucket)

        self.logger.debug("groupID:{0},buckets:{1}".format(groupID,buckets))
        self.logger.debug("datapath:{0}".format(datapath))
        req = parser.OFPGroupMod(datapath, ofproto.OFPGC_ADD,
                                    ofproto.OFPGT_FF, groupID, buckets)
        datapath.send_msg(req)

    def _getNewVLANID(self, currentDpid, nextDpid, sfci, direction):
        primaryPathID = self._getPathID(direction["ID"])
        backupPaths = self._getBackupPaths(sfci,primaryPathID)
        for key in backupPaths.iterkeys():
            if key[0] == currentDpid and key[1] == nextDpid:
                pathID = key[2]
                return self.ibm.assignVLANID(sfci.SFCIID, pathID)
        else:
            return None

    def _addNotViaSFCIFlowtable(self, currentDpid, SFCIID, dstIP, groupID):
        self.logger.debug("_addNotViaSFCIFlowtable")
        datapath = self.dpset.get(int(str(currentDpid),0))
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        matchFields = {'eth_type':ether_types.ETH_TYPE_IP,
            'ipv4_dst':dstIP}
        match = parser.OFPMatch(**matchFields)

        actions = [parser.OFPActionGroup(groupID)]
        inst = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)
        ]
        self._add_flow(datapath, match, inst, table_id=NotVia_TABLE,
            priority = 1)
        self.ibm.addSFCIFlowTableEntry(SFCIID,currentDpid,
            NotVia_TABLE, matchFields, groupID)

    def _installBackupPaths(self, sfci, direction):
        primaryPathID = self._getPathID(direction["ID"])
        backupFPs = self._getBackupPaths(sfci,primaryPathID)
        for key,value in backupFPs.items():
            (currentID, nextID, pathID) = key
            FP = value
            sfciLength = len(sfci.VNFISequence)
            fpLength = len(FP)
            stageCount = sfciLength - fpLength
            self.logger.debug("_installBackupPaths")
            self.logger.debug(FP)
            for stage in FP:
                stageCount = stageCount + 1
                if len(stage)==2:
                    # SFF inner routing
                    continue
                vlanID = self.ibm.getVLANID(sfci.SFCIID, pathID)
                for i in range(1,len(stage)-1):
                    currentSwitchID = stage[i]
                    nextNodeID = stage[i+1]
                    self._installRouteOnBackupPath(sfci, direction,
                        currentSwitchID, nextNodeID, vlanID)
                    if i == len(stage)-2:
                        self._installLastRouteOnBackupPath(sfci, direction,
                                nextNodeID, vlanID)

    def _installRouteOnBackupPath(self, sfci, direction, currentDpid,
            nextDpid, vlanID):
        self.logger.debug("**********************")
        self.logger.debug("_installRouteOnBackupPath")
        self.logger.debug(currentDpid)
        datapath = self.dpset.get(int(str(currentDpid), 0))
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        # matchFields={'eth_type':ether_types.ETH_TYPE_8021Q, 'vlan_vid':vlanID}
        matchFields={'vlan_vid':vlanID}
        # match = parser.OFPMatch(**matchFields)

        match = parser.OFPMatch()
        match.set_vlan_vid(vlanID)

        # get default src/dst ether and default OutPort
        (srcMAC,dstMAC,defaultOutPort) = self._getNextHopActionFields(sfci,
            direction, currentDpid, nextDpid)
        if defaultOutPort == None:
            raise ValueError("NotVia: can not get default out port")
        self.logger.debug("srcMAC:{0}, dstMAC:{1}, outport:{2}".format(srcMAC, dstMAC,
            defaultOutPort))
        actions = [
            parser.OFPActionSetField(eth_src=srcMAC),
            parser.OFPActionSetField(eth_dst=dstMAC),
        ]

        inst = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                actions),
            parser.OFPInstructionGotoTable(table_id=L2_TABLE)
        ]

        self.logger.debug("_packet_in_handler: Add_flow")
        self._add_flow(datapath, match, inst, table_id=VLAN_TABLE,
            priority=1)
        self.ibm.addSFCIFlowTableEntry(sfci.SFCIID,currentDpid,
            VLAN_TABLE, matchFields)

    def _installLastRouteOnBackupPath(self, sfci, direction, currentDpid,
            vlanID):
        self.logger.debug("_installLastRouteOnBackupPath")
        self.logger.debug(currentDpid)
        datapath = self.dpset.get(int(str(currentDpid), 0))
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        # matchFields={'eth_type':ether_types.ETH_TYPE_8021Q, 'vlan_vid':vlanID}
        matchFields={'vlan_vid':vlanID}
        # match = parser.OFPMatch(**matchFields)

        match = parser.OFPMatch()
        # eth_VLAN = ether_types.ETH_TYPE_8021Q
        # match.set_dl_type(eth_VLAN)
        self.logger.debug("vlanID:{0}".format(vlanID))
        match.set_vlan_vid(vlanID)
        actions = [parser.OFPActionPopVlan()]

        inst = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                actions),
            parser.OFPInstructionGotoTable(table_id=NotVia_TABLE)
        ]

        self.logger.debug("_packet_in_handler: Add_flow")
        self._add_flow(datapath, match, inst, table_id=VLAN_TABLE,
            priority=1)
        self.ibm.addSFCIFlowTableEntry(sfci.SFCIID,currentDpid,
            VLAN_TABLE, matchFields)




    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _switchFeaturesHandler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id

        # install table-miss flow entry in NotVia_TABLE
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
        self._add_flow(datapath, match, inst, table_id = NotVia_TABLE,
            priority=0)

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        self._add_flow(datapath, match, inst, table_id = VLAN_TABLE,
            priority=0)

        # initial IPv4_CLASSIFIER_TABLE
        match = parser.OFPMatch(
            eth_type=ether_types.ETH_TYPE_IP,ipv4_dst="10.0.0.0/8"
        )
        inst = [parser.OFPInstructionGotoTable(table_id = NotVia_TABLE)]
        self._add_flow(datapath, match, inst,
            table_id = IPv4_CLASSIFIER_TABLE, priority=2)

    def _sendCmdRply(self, cmdID, cmdState):
        cmdRply = CommandReply(cmdID, cmdState)
        rplyMsg = SAMMessage(MSG_TYPE_NETWORK_CONTROLLER_CMD_REPLY, cmdRply)
        queue = MEDIATOR_QUEUE
        self._messageAgent.sendMsg(queue, rplyMsg)
