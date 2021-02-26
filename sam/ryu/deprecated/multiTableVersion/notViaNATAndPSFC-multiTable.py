#!/usr/bin/python
# -*- coding: UTF-8 -*-

import copy
import time

from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.controller import dpset
from ryu.controller import event as ryuControllerEvent
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
from sam.ryu.notViaNATIBMaintainer import NotViaNATIBMaintainer
from sam.ryu.frr import FRR
from sam.base.messageAgent import *
from sam.base.command import *
from sam.base.path import *
from sam.base.socketConverter import *
from sam.base.vnf import *
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.serverController.serverManager.serverManager import *


class NotViaNATAndPSFC(FRR):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {
        'dpset': dpset.DPSet,
        'TopoCollector': TopoCollector
        }

    def __init__(self, *args, **kwargs):
        super(NotViaNATAndPSFC, self).__init__(*args, **kwargs)
        self.logger.info("Initialize NotViaNATAndPSFC App !")
        self.ibm = NotViaNATIBMaintainer()
        self.logger.info("NotViaNATAndPSFC App is running !")

    def _addSFCHandler(self, cmd):
        self.logger.debug(
            '*** NotViaNATAndPSFC App Received command={0}'.format(cmd))
        try:
            sfc = cmd.attributes['sfc']
            self._addRoute2Classifier(sfc)
            self._sendCmdRply(cmd.cmdID, CMD_STATE_SUCCESSFUL)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                "Ryu app NotViaNATAndPSFC _addSFCHandler ")
            self._sendCmdRply(cmd.cmdID, CMD_STATE_FAIL)

    def _addSFCIHandler(self, cmd):
        self.logger.debug(
            '*** NotViaNATAndPSFC App Received command={0}'.format(cmd))
        try:
            sfc = cmd.attributes['sfc']
            sfci = cmd.attributes['sfci']
            self._addSFCIRoute(sfc, sfci)
            self._sendCmdRply(cmd.cmdID, CMD_STATE_SUCCESSFUL)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                "Ryu app NotViaNATAndPSFC _addSFCIHandler ")
            self._sendCmdRply(cmd.cmdID, CMD_STATE_FAIL)

    def _addSFCIRoute(self, sfc, sfci):
        # install sfci path
        for direction in sfc.directions:
            # install primary path route
            self._installPrimaryPath(sfci, direction)
            # install backup paths route
            self._installBackupPaths(sfci, direction)
            # install pSFC paths route
            self._installPSFCPaths(sfci, direction)
        return True

    def _installPrimaryPath(self, sfci, direction):
        primaryPathID = self._getPathID(direction["ID"])
        primaryFP = self._getPrimaryPath(sfci, primaryPathID)
        stageCount = -1
        for segPath in primaryFP:
            stageCount = stageCount + 1
            if self._isInnerNFVISegPath(segPath):
                # SFF inner routing
                continue
            dstIP = self.getSFCIStageDstIP(sfci, stageCount, primaryPathID)
            (srcServerID,dstServerID) = self._getSrcDstServerInStage(segPath)
            # add route
            for i in range(1,len(segPath)-1):
                currentSwitchID = segPath[i][1]
                groupID = self.ibm.assignGroupID(currentSwitchID)
                self.logger.debug("dpid:{0}".format(currentSwitchID))
                self.logger.debug("assignGroupID:{0}".format(groupID))
                nextNodeID = segPath[i+1][1]

                if self._canSkipPrimaryPathFlowInstallation(sfci.sfciID,
                    dstIP, currentSwitchID):
                    continue

                self._addNotViaSFCIGroupTable(currentSwitchID,
                    nextNodeID, sfci, direction, stageCount, groupID)
                self._addNotViaSFCIFlowtable(currentSwitchID,
                    sfci.sfciID, dstIP, groupID)

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
            raise ValueError("NotViaNATAndPSFC: can not get default out port")
        self.logger.debug("Bucket1")
        self.logger.debug("srcMAC:{0},dstMAC:{1},outport:{2}".format(srcMAC,dstMAC,
            defaultOutPort))
        actions = [
            # parser.OFPActionDecNwTtl(),
            parser.OFPActionSetField(eth_src=srcMAC),
            parser.OFPActionSetField(eth_dst=dstMAC),
            parser.OFPActionOutput(defaultOutPort)
        ]
        watch_port = defaultOutPort
        bucket = parser.OFPBucket(watch_port=watch_port,actions=actions)
        buckets.append(bucket)

        # get backup src/dst ether, backup OutPort and new dstIP
        backupnextDpid = self._getBackupNextHop(currentDpid, nextDpid, sfci,
            direction, stageCount)
        self.logger.debug("backupnextDpid:{0}".format(backupnextDpid))
        if backupnextDpid != None:
            newDstIP = self._getNewDstIP(currentDpid, nextDpid, sfci,
                direction, stageCount)
            (srcMAC, dstMAC, backupOutPort) = self._getNextHopActionFields(
                sfci, direction, currentDpid, backupnextDpid)

            self.logger.debug("Bucket2")
            self.logger.info("srcMAC:{0}, dstMAC:{1},"
                    " newDstIP:{2}, outport:{3}".format(
                        srcMAC, dstMAC, newDstIP, backupOutPort))
            actions = [
                # parser.OFPActionDecNwTtl(),
                parser.OFPActionSetField(eth_src=srcMAC),
                parser.OFPActionSetField(eth_dst=dstMAC),
                parser.OFPActionSetField(ipv4_dst=newDstIP),
                parser.OFPActionOutput(backupOutPort)
            ]
            watch_port = backupOutPort
            bucket = parser.OFPBucket(watch_port=watch_port, actions=actions)
            buckets.append(bucket)

        self.logger.debug("groupID:{0}, buckets:{1}".format(groupID, buckets))
        self.logger.debug("datapath.id:{0}".format(datapath.id))
        req = parser.OFPGroupMod(datapath, ofproto.OFPGC_ADD,
                                    ofproto.OFPGT_FF, groupID, buckets)
        datapath.send_msg(req)

    def _getNewDstIP(self, currentDpid, nextDpid, sfci, direction,
            stageCount):
        primaryPathID = self._getPathID(direction["ID"])
        backupPaths = self._getBackupPaths(sfci, primaryPathID)
        for key in backupPaths.iterkeys():
            (repairSwitchID, failureNodeID, newPathID) \
                = self._getRepairSwitchIDAndFailureNodeIDAndNewPathIDFromKey(key)
            if repairSwitchID == currentDpid and failureNodeID == nextDpid:
                self.logger.info("_getNewDstIP")
                return self.getSFCIStageDstIP(sfci, stageCount, newPathID)
        else:
            return None

    def _addNotViaSFCIFlowtable(self, currentDpid, sfciID, dstIP, groupID):
        self.logger.debug("_addNotViaSFCIFlowtable")
        datapath = self.dpset.get(int(str(currentDpid),0))
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        matchFields = {
            'eth_type':ether_types.ETH_TYPE_IP,
            'ipv4_dst':dstIP}
        match = parser.OFPMatch(**matchFields)

        actions = [parser.OFPActionGroup(groupID)]
        inst = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)
        ]
        self._add_flow(datapath, match, inst, table_id=NOTVIAPSFC_TABLE,
                        priority = 1)
        self.ibm.addSFCIFlowTableEntry(sfciID, currentDpid,
            NOTVIAPSFC_TABLE, matchFields, groupID)

    def _installBackupPaths(self, sfci, direction):
        primaryPathID = self._getPathID(direction["ID"])
        backupFPs = self._getBackupPaths(sfci, primaryPathID)
        for key, backupPath in backupFPs.items():
            if self._isPSFCBackupPath(key):
                continue
            pathID = self._getNewPathID4Key(key)
            self.logger.debug("_installBackupPaths")
            self.logger.debug(backupPath)
            for segPath in backupPath:
                if self._isInnerNFVISegPath(segPath):
                    # SFF inner routing
                    continue
                dstIP = self.getSFCIStageDstIP(sfci, stageCount, pathID)
                for i in range(1, len(segPath)-1):
                    currentSwitchID = segPath[i][1]
                    nextNodeID = segPath[i+1][1]
                    self._installRouteOnBackupPath(sfci, direction,
                        currentSwitchID, nextNodeID, dstIP)
                    if i == len(segPath)-2:
                        self._installLastRouteOnBackupPath(sfci, direction,
                            nextNodeID, dstIP)

    def _installRouteOnBackupPath(self, sfci, direction, currentDpid,
            nextDpid, dstIP):
        self.logger.debug("_installRouteOnBackupPath")
        self.logger.info("currentDpid:{0}".format(currentDpid))
        datapath = self.dpset.get(int(str(currentDpid), 0))
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        matchFields={'eth_type': ether_types.ETH_TYPE_IP,
            'ipv4_dst':dstIP+"/32"}
        match = parser.OFPMatch(**matchFields)

        # get default src/dst ether and default OutPort
        (srcMAC, dstMAC, defaultOutPort) = self._getNextHopActionFields(
            sfci, direction, currentDpid, nextDpid)
        if defaultOutPort == None:
            raise ValueError("NotViaNATAndPSFC: can not get default out port")
        self.logger.debug(
            "srcMAC:{0}, dstMAC:{1}, outport:{2}".format(
                srcMAC, dstMAC, defaultOutPort))
        actions = [
            # parser.OFPActionDecNwTtl(),
            parser.OFPActionSetField(eth_src=srcMAC),
            parser.OFPActionSetField(eth_dst=dstMAC),
        ]

        inst = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                actions),
            parser.OFPInstructionGotoTable(table_id=L2_TABLE)
        ]

        self.logger.debug("_installRouteOnBackupPath Add_flow")
        self._add_flow(datapath, match, inst, table_id=NOTVIAPSFC_TABLE,
            priority=2)
        self.ibm.addSFCIFlowTableEntry(sfci.sfciID, currentDpid,
            NOTVIAPSFC_TABLE, matchFields)

    def _installLastRouteOnBackupPath(self, sfci, direction,
                                        currentDpid, dstIP):
        self.logger.debug("_installLastRouteOnBackupPath")
        self.logger.debug("dstIP:{0}".format(dstIP))
        self.logger.debug(currentDpid)
        datapath = self.dpset.get(int(str(currentDpid), 0))
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        matchFields={'eth_type':ether_types.ETH_TYPE_IP,
            'ipv4_dst':dstIP+"/32"}
        match = parser.OFPMatch(**matchFields)

        # get default src/dst ether and default OutPort
        (srcMAC, dstMAC, defaultOutPort) = self._getNextHopActionFields(
            sfci, direction, currentDpid, nextDpid)
        if defaultOutPort == None:
            raise ValueError("UFRR: can not get default out port")
        self.logger.info(
            "srcMAC:{0}, dstMAC:{1}, outport:{2}".format(
                srcMAC, dstMAC, defaultOutPort))
        actions = [
            # parser.OFPActionDecNwTtl(),
            parser.OFPActionSetField(eth_src=srcMAC),
            parser.OFPActionSetField(eth_dst=dstMAC),
            parser.OFPActionSetField(ipv4_dst=newDstIP)
        ]

        inst = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                actions),
            parser.OFPInstructionGotoTable(table_id=NOTVIAPSFC_TABLE)
        ]

        # WARNINGS! We find that OvS doesn't support MPLS POP following a goto table.
        # Flow doesn't match the entry in NOTVIAPSFC_TABLE
        # We design a possible method to tackle this problem:
        # store the mapping relation
        #           groupID <-> switchID + (sfci.sfciID, pathID) <-> mplsLabel
        # Then, use following code replace above code:
        # groupID = self.groupIDMaintainer.getGroupID(currentDpid, sfci.sfciID, pathID)
        # actions = [
        #   parser.OFPActionPopMpls(ether_types.ETH_TYPE_IP),
        #   parser.OFPActionGroup(groupID)
        # ]
        # 
        # inst = [
        #     parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)
        # ]
        # However, we find that PICA8 switch doesn't support MPLS only forwarding
        # https://docs.pica8.com/display/picos2102cg/Configuring+MPLS
        # It needs VLAN support, but we use virtual bridge function which is confilct
        # with this scenario.
        # All in all, We tend to use nat to realize notvia and PSFC.

        self.logger.debug("_installLastRouteOnBackupPath Add_flow")
        self._add_flow(datapath, match, inst, table_id=NOTVIAPSFC_TABLE,
            priority=2)
        self.ibm.addSFCIFlowTableEntry(sfci.sfciID, currentDpid,
            NOTVIAPSFC_TABLE, matchFields)

    def _installPSFCPaths(self, sfci,direction):
        # TODO: test NotVia first, if it is succesful, then implement this function
        pass

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _switchFeaturesHandler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id

        # install table-miss flow entry in NOTVIAPSFC_TABLE
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
        self._add_flow(datapath, match, inst, table_id = NOTVIAPSFC_TABLE,
            priority=0)

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        self._add_flow(datapath, match, inst, table_id = MPLS_TABLE,
            priority=0)

        # initial IPV4_CLASSIFIER_TABLE
        match = parser.OFPMatch(
            eth_type=ether_types.ETH_TYPE_IP,ipv4_dst="10.0.0.0/8"
        )
        inst = [parser.OFPInstructionGotoTable(table_id = NOTVIAPSFC_TABLE)]
        self._add_flow(datapath, match, inst,
            table_id = IPV4_CLASSIFIER_TABLE, priority=3)

    def _sendCmdRply(self, cmdID, cmdState):
        cmdRply = CommandReply(cmdID, cmdState)
        rplyMsg = SAMMessage(MSG_TYPE_NETWORK_CONTROLLER_CMD_REPLY, cmdRply)
        queue = MEDIATOR_QUEUE
        self._messageAgent.sendMsg(queue, rplyMsg)
