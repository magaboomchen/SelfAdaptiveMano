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
from sam.ryu.ufrrIBMaintainer import *
from sam.ryu.frr import FRR
from sam.base.messageAgent import *
from sam.base.command import *
from sam.base.path import *
from sam.base.socketConverter import *
from sam.base.vnf import *
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.serverController.serverManager.serverManager import *


class UFRR(FRR):
    def __init__(self, *args, **kwargs):
        super(UFRR, self).__init__(*args, **kwargs)
        self.logger.info("Initialize UFRR App !")
        self.ibm = UFRRIBMaintainer()
        self.logger.info("UFRR App is running !")

    def _addSFCHandler(self, cmd):
        self.logger.debug(
            '*** FRR App Received command={0}'.format(cmd))
        try:
            sfc = cmd.attributes['sfc']
            self._addRoute2Classifier(sfc)
            self._sendCmdRply(cmd.cmdID, CMD_STATE_SUCCESSFUL)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                "Ryu app UFRR _addSFCHandler ")
            self._sendCmdRply(cmd.cmdID, CMD_STATE_FAIL)
        finally:
            pass

    def _addSFCIHandler(self, cmd):
        self.logger.debug(
            '*** FRR App Received command={0}'.format(cmd))
        try:
            sfc = cmd.attributes['sfc']
            sfci = cmd.attributes['sfci']
            self._addSFCIRoute(sfc, sfci)
            self._sendCmdRply(cmd.cmdID, CMD_STATE_SUCCESSFUL)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                "Ryu app UFRR _addSFCIHandler ")
            self._sendCmdRply(cmd.cmdID, CMD_STATE_FAIL)
        finally:
            pass

    def _addSFCIRoute(self, sfc, sfci):
        # install sfci path
        for direction in sfc.directions:
            # install primary path route
            self._installPrimaryPath(sfci, direction)
            # install backup paths route
            self._installBackupPaths(sfci, direction)
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
            (srcServerID, dstServerID) = self._getSrcDstServerInStage(segPath)
            # add route
            for i in range(1, len(segPath)-1):
                currentSwitchID = segPath[i][1]
                groupID = self.ibm.assignGroupID(currentSwitchID)
                self.logger.info("dpid:{0}".format(currentSwitchID))
                self.logger.info("assignGroupID:{0}".format(groupID))
                nextNodeID = segPath[i+1][1]

                if self._canSkipPrimaryPathFlowInstallation(sfci.sfciID,
                        dstIP, currentSwitchID):
                    continue

                self._addUFRRSFCIGroupTable(currentSwitchID,
                    nextNodeID, sfci, direction, stageCount, groupID)
                self._addUFRRSFCIFlowtable(currentSwitchID,
                    sfci, stageCount, primaryPathID, dstIP, groupID)

    def _addUFRRSFCIGroupTable(self, currentDpid, nextDpid, sfci,
                                direction, stageCount, groupID):
        datapath = self.dpset.get(int(str(currentDpid),0))
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        buckets = []
        # get default src/dst ether and default OutPort
        (srcMAC, dstMAC, defaultOutPort) = self._getNextHopActionFields(sfci,
            direction, currentDpid, nextDpid)
        if defaultOutPort == None:
            raise ValueError("UFRR: can not get default out port")
        self.logger.info("Bucket1")
        self.logger.info("srcMAC:{0}, dstMAC:{1}, outport:{2}".format(
            srcMAC, dstMAC, defaultOutPort))
        actions = [
            # parser.OFPActionDecNwTtl(),
            parser.OFPActionSetField(eth_src=srcMAC),
            parser.OFPActionSetField(eth_dst=dstMAC),
            parser.OFPActionOutput(defaultOutPort)
        ]
        watch_port = defaultOutPort
        bucket = parser.OFPBucket(watch_port=watch_port, actions=actions)
        buckets.append(bucket)

        # get backup src/dst ether, backup OutPort and new dstIP
        backupnextDpid = self._getBackupNextHop(currentDpid, nextDpid, sfci,
            direction, stageCount)
        self.logger.info("backupnextDpid:{0}".format(backupnextDpid))
        if backupnextDpid != None:
            newDstIP = self._getNewDstIP(currentDpid, nextDpid, sfci,
                direction, stageCount)
            (srcMAC, dstMAC, backupOutPort) = self._getNextHopActionFields(
                sfci, direction, currentDpid, backupnextDpid)

            self.logger.info("Bucket2")
            self.logger.info("srcMAC:{0}, dstMAC:{1},"
                    " newDstIP:{2}, outport:{3}".format(
                        srcMAC, dstMAC, newDstIP, backupOutPort))
            actions = [
                # parser.OFPActionDecNwTtl(),
                parser.OFPActionSetField(eth_src=srcMAC),
                parser.OFPActionSetField(eth_dst=dstMAC),
                parser.OFPActionSetField(ipv4_dst=newDstIP),
                # only available for openflow 1.5
                # parser.OFPActionSetField(ipv4_dst=(newDstIP,"0.0.0.255")),
                parser.OFPActionOutput(backupOutPort)
            ]
            watch_port = backupOutPort
            bucket = parser.OFPBucket(watch_port=watch_port, actions=actions)
            buckets.append(bucket)

        self.logger.info("groupID:{0}, buckets:{1}".format(groupID, buckets))
        self.logger.info("datapath:{0}".format(datapath))
        req = parser.OFPGroupMod(datapath, ofproto.OFPGC_ADD,
                                    ofproto.OFPGT_FF, groupID, buckets)
        datapath.send_msg(req)

    def _addUFRRSFCIFlowtable(self, currentDpid, sfci, stageCount,
                                pathID, dstIP, groupID):
        self.logger.info("_addUFRRSFCIFlowtable")
        sfciID = sfci.sfciID
        datapath = self.dpset.get(int(str(currentDpid),0))
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        matchFields = {'eth_type': ether_types.ETH_TYPE_IP,
            'ipv4_dst': dstIP}
        match = parser.OFPMatch(**matchFields)

        actions = [
            parser.OFPActionGroup(groupID)
        ]
        inst = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)
        ]
        self._add_flow(datapath, match, inst, table_id=UFRR_TABLE,
            priority = 1)
        vnfID = sfci.getVNFTypeByStageNum(stageCount)
        self.ibm.addSFCIUFRRFlowTableEntry(
            currentDpid, sfciID, vnfID, pathID, {"goto group": groupID}
        )

    def _getNewDstIP(self, currentDpid, nextDpid, sfci, direction,
            stageCount):
        primaryPathID = self._getPathID(direction["ID"])
        backupPaths = self._getBackupPaths(sfci,primaryPathID)
        for key in backupPaths.iterkeys():
            (repairSwitchID, failureNodeID, newPathID) \
                = self._getRepairSwitchIDAndFailureNodeIDAndNewPathIDFromKey(key)
            if repairSwitchID == currentDpid and failureNodeID == nextDpid:
                self.logger.info("_getNewDstIP")
                return self.getSFCIStageDstIP(sfci, stageCount, newPathID)
        else:
            return None

    def _installBackupPaths(self, sfci, direction):
        primaryPathID = self._getPathID(direction["ID"])
        backupFPs = self._getBackupPaths(sfci, primaryPathID)
        for key, backupPath in backupFPs.items():
            pathID = self._getNewPathIDFromKey(key)
            sfciLength = len(sfci.vnfiSequence)
            fpLength = len(backupPath)
            stageCount = sfciLength - fpLength
            self.logger.info("_installBackupPaths")
            for segPath in backupPath:
                stageCount = stageCount + 1
                if self._isInnerNFVISegPath(segPath):
                    # SFF inner routing
                    continue
                dstIP = self.getSFCIStageDstIP(sfci, stageCount, pathID)
                for i in range(1,len(segPath)-1):
                    currentSwitchID = segPath[i][1]
                    nextNodeID = segPath[i+1][1]
                    self._installRouteOnBackupPath(sfci, direction,
                        currentSwitchID, nextNodeID, dstIP, pathID,
                        stageCount)

    def _getNewPathIDFromKey(self, key):
        if key[3][0] == "newPathID":
            return key[3][1]
        else:
            raise ValueError("Unknown key")

    def _installRouteOnBackupPath(self, sfci, direction, currentDpid,
            nextDpid, dstIP, pathID, stageCount):
        self.logger.info("_installRouteOnBackupPath")
        self.logger.info("currentDpid:{0}".format(currentDpid))
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
        ]

        inst = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                actions),
            parser.OFPInstructionGotoTable(table_id=L2_TABLE)
        ]

        self.logger.debug("_installRouteOnBackupPath Add_flow")
        self._add_flow(datapath, match, inst, table_id=UFRR_TABLE,
            priority=2)
        vnfID = sfci.getVNFTypeByStageNum(stageCount)
        self.ibm.addSFCIUFRRFlowTableEntry(
            currentDpid, sfci.sfciID, vnfID, pathID,
            {"output nodeID": nextDpid}
        )

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _switchFeaturesHandler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id

        # install table-miss flow entry in UFRR_TABLE
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
        self._add_flow(datapath, match, inst, table_id = UFRR_TABLE, priority=0)

        # initial IPV4_CLASSIFIER_TABLE
        match = parser.OFPMatch(
            eth_type=ether_types.ETH_TYPE_IP,ipv4_dst="10.0.0.0/8"
        )
        inst = [parser.OFPInstructionGotoTable(table_id = UFRR_TABLE)]
        self._add_flow(datapath, match, inst, table_id = IPV4_CLASSIFIER_TABLE, priority=3)

    def _sendCmdRply(self, cmdID, cmdState):
        cmdRply = CommandReply(cmdID,cmdState)
        cmdRply.attributes["source"] = {"ryu uffr"}
        rplyMsg = SAMMessage(MSG_TYPE_NETWORK_CONTROLLER_CMD_REPLY,cmdRply)
        queue = MEDIATOR_QUEUE
        self._messageAgent.sendMsg(queue,rplyMsg)
