#!/usr/bin/python
# -*- coding: UTF-8 -*-

import copy
import time

from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.controller import dpset
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import ether_types
from ryu.topology import event, switches

from sam.ryu.topoCollector import TopoCollector, TopologyChangeEvent
from sam.ryu.conf.ryuConf import *
from sam.ryu.notViaNATIBMaintainer import NotViaNATIBMaintainer
from sam.ryu.pSFCIBMaintainer import *
from sam.ryu.frr import FRR
from sam.base.messageAgent import *
from sam.base.command import *
from sam.base.path import *
from sam.base.socketConverter import SocketConverter, BCAST_MAC
from sam.base.vnf import *
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.serverController.serverManager.serverManager import SeverManager, SERVERID_OFFSET


class PSFC(FRR):
    def __init__(self, *args, **kwargs):
        super(PSFC, self).__init__(*args, **kwargs)
        logConfigur = LoggerConfigurator(__name__, './log',
                                        'pSFC.log', level='info')
        self.logger = logConfigur.getLogger()
        self.logger.info("Initialize PSFC App !")
        self.ibm = NotViaNATIBMaintainer()
        self.pSFCIbm = PSFCIBMaintainer()
        self.logger.info("PSFC App is running !")

    def _addSFCHandler(self, cmd):
        self.logger.debug(
            '*** PSFC App Received command={0}'.format(cmd))
        try:
            sfc = cmd.attributes['sfc']
            self.logger.info("add sfc: {0}".format(sfc.sfcUUID))
            self._addRoute2Classifier(sfc)
            self._sendCmdRply(cmd.cmdID, CMD_STATE_SUCCESSFUL)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                "Ryu app PSFC _addSFCHandler ")
            self._sendCmdRply(cmd.cmdID, CMD_STATE_FAIL)

    def _serverStatusChangeHandler(self, cmd):
        self.logger.debug(
            "*** FRR App Received server status change"
            " command={0}".format(cmd))
        try:
            serverDownList = cmd.attributes['serverDown']
            self._tackleServerFailure(serverDownList)
            # TODO: process serverUp in the future
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                "Ryu app PSFC _serverStatusChangeHandler ")
        finally:
            pass

    def _tackleServerFailure(self, serverDownList):
        for server in serverDownList:
            serverID = server.getServerID()
            self._pSFCHandleNodeFailure(serverID)

    def _pSFCHandleNodeFailure(self, nodeID):
        affectedSFCIIDBpTupleList \
            = self._getAffectedSFCIIDBpTupleListByFailureNodeID(nodeID)
        self.logger.debug("affcted sfciID bp tuple list:{0}".format(affectedSFCIIDBpTupleList))
        for sfciBpTuple in affectedSFCIIDBpTupleList:
            (sfciID, backupPathKey) = sfciBpTuple
            self._increaseSFCIBackupPathPriority(sfciID, backupPathKey)

    def _getAffectedSFCIIDBpTupleListByFailureNodeID(self, failureNodeID):
        affectedSFCIIDBpTupleList = []
        sfciDict = self.pSFCIbm.getSFCIDict()
        for sfciID, sfci in sfciDict.items():
            for directionID in [0,1]:
                # try:
                primaryPathID = self._getPathID(directionID)
                primaryFP = self._getPrimaryPath(sfci, primaryPathID)
                backupFPs = self._getBackupPaths(sfci, primaryPathID)
                if primaryFP == None or backupFPs == None:
                    continue
                else:
                    self.logger.debug("valid primaryPathID")
                # except Exception as ex:
                #     ExceptionProcessor(self.logger).logException(ex)
                if failureNodeID >= SERVERID_OFFSET:
                    self.logger.debug("failure node {0} is a server".format(
                                        failureNodeID))
                    # find sff in primaryPath
                    # search key in backupPathSet
                    # store (sfciID, key) affectedSFCIIDBpTupleList
                    for segPathIndex in range(len(primaryFP)-1):
                        segPath = primaryFP[segPathIndex]
                        (layerNum, serverID) = segPath[-1]
                        if serverID != failureNodeID:
                            continue
                        layerBpID = segPath[-2]
                        for key, backupPath in backupFPs.items():
                            if not self._isPSFCBackupPath(key):
                                continue
                            keyDict = self._parseBackupPathKey(key)
                            (layerNum, bp, xp) = keyDict["failureNPoPID"]
                            self.logger.debug("failureNPoPID:{0}".format(
                                keyDict["failureNPoPID"]))
                            if (layerNum, bp) == layerBpID:
                                affectedSFCIIDBpTupleList.append((sfciID, key))
                else:
                    self.logger.debug("failure node {0} is a switch".format(
                                        failureNodeID))
                    # TODO: we only implement one direction
                    for key, backupPath in backupFPs.items():
                        if not self._isPSFCBackupPath(key):
                            continue
                        keyDict = self._parseBackupPathKey(key)
                        (layerNum, bp, xp) = keyDict["failureNPoPID"]
                        if bp == failureNodeID:
                            affectedSFCIIDBpTupleList.append((sfciID, key))
        return affectedSFCIIDBpTupleList

    def _increaseSFCIBackupPathPriority(self, sfciID, backupPathKey):
        self.logger.debug("_increaseSFCIBackupPathPriority")
        dpidFIBEntryDict \
            = self.pSFCIbm.getSFCIFlowTableEntries(sfciID, backupPathKey)
        for dpid, entryList in dpidFIBEntryDict.items():
            datapath = self.dpset.get(int(str(dpid), 0))
            for entry in entryList:
                tableID = entry["tableID"]
                matchFields = entry["matchFields"]
                parser = datapath.ofproto_parser
                match = parser.OFPMatch(**matchFields)
                priority = entry["priority"]
                actions = entry["actions"]
                # TODO: hard code, please judge actions' type, e.g. outport or group
                outPort = actions[-1].port
                inst = entry["inst"]
                if priority == LOWER_BACKUP_ENTRY_PRIORITY:
                    self.logger.debug(
                        "_del_flow dpid:{0}, match:{1}, priority:{2}".format(
                            dpid, match, priority))
                    self._del_flow(datapath, match, tableID, priority, outPort=outPort)
                    self.syncDatapath(datapath)
                    self._add_flow(datapath, match, inst, tableID,
                                    priority=UPPER_BACKUP_ENTRY_PRIORITY)
                    self.syncDatapath(datapath)
                    priority = UPPER_BACKUP_ENTRY_PRIORITY

    def _addSFCIHandler(self, cmd):
        self.logger.debug(
            '*** PSFC App Received command={0}'.format(cmd))
        try:
            sfc = cmd.attributes['sfc']
            sfci = cmd.attributes['sfci']
            self.logger.info("add sfci: {0}".format(sfci.sfciID))
            self._addSFCIRoute(sfc, sfci)
            self.pSFCIbm.addSFCI(sfci)
            self._sendCmdRply(cmd.cmdID, CMD_STATE_SUCCESSFUL)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                "Ryu app PSFC _addSFCIHandler ")
            self._sendCmdRply(cmd.cmdID, CMD_STATE_FAIL)

    def _addSFCIRoute(self, sfc, sfci):
        # install sfci path
        for direction in sfc.directions:
            # install primary path route
            self._installPrimaryPath(sfci, direction)

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
                prevNodeID = segPath[i-1][1]
                currentSwitchID = segPath[i][1]
                inPortIndex = self._getInputPortOfDstNode(sfci, direction,
                                                            prevNodeID, currentSwitchID)
                self.logger.debug(
                    "inPortIndex:{0} prevNodeID:{1}, currentSwitchID:{2}".format(
                        inPortIndex, prevNodeID, currentSwitchID))
                groupID = self.ibm.assignGroupID(currentSwitchID)
                self.logger.debug("dpid:{0}".format(currentSwitchID))
                self.logger.debug("assignGroupID:{0}".format(groupID))
                nextNodeID = segPath[i+1][1]

                if self._canSkipPrimaryPathFlowInstallation(sfci.sfciID,
                    dstIP, currentSwitchID):
                    continue

                self._addNotViaSFCIFlowtable(currentSwitchID,
                    sfci, direction, inPortIndex, dstIP, nextNodeID)

    def _addNotViaSFCIFlowtable(self, currentDpid, sfci, direction, inPortIndex, dstIP, nextNodeID):
        sfciID = sfci.sfciID
        self.logger.debug("_addNotViaSFCIFlowtable")
        datapath = self.dpset.get(int(str(currentDpid),0))
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        matchFields = {
            'in_port': inPortIndex,
            'eth_type':ether_types.ETH_TYPE_IP,
            'ipv4_dst':dstIP}
        match = parser.OFPMatch(**matchFields)
        (srcMAC, dstMAC, defaultOutPort) \
            = self._getNextHopActionFields(sfci, direction, currentDpid,
                                            nextNodeID)
        actions = [
            parser.OFPActionSetField(eth_src=srcMAC),
            parser.OFPActionSetField(eth_dst=dstMAC),
            parser.OFPActionOutput(defaultOutPort)
        ]
        inst = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)
        ]
        self._add_flow(datapath, match, inst,
                        table_id=MAIN_TABLE, priority=3)
        self.ibm.addSFCIFlowTableEntry(sfciID, currentDpid,
                                        MAIN_TABLE, matchFields, nextNodeID)

    def _getStageCount4Key(self, key):
        keyDict = self._parseBackupPathKey(key)
        if "repairLayerSwitchID" in keyDict.keys():
            (layerNum, repairSwitchID) = keyDict["repairLayerSwitchID"]
        elif "failureNPoPID" in keyDict.keys():
            (layerNum, bp, xp) = keyDict["failureNPoPID"]
        else:
            layerNum = None
        return layerNum

    def _installPSFCPaths(self, sfci, direction):
        primaryPathID = self._getPathID(direction["ID"])
        primaryFP = self._getPrimaryPath(sfci, primaryPathID)
        backupFPs = self._getBackupPaths(sfci, primaryPathID)
        for key, backupPath in backupFPs.items():
            if not self._isPSFCBackupPath(key):
                continue
            pathID = primaryPathID
            stageCount = self._getStageCount4Key(key)
            self.logger.debug("_installPSFCPaths:{0}".format(backupPath))
            for idx, segPath in enumerate(backupPath):
                self.logger.debug("going to install PSFC's stage {0}".format(stageCount))
                if self._isInnerNFVISegPath(segPath):
                    # SFF inner routing
                    continue
                dstIP = self.getSFCIStageDstIP(sfci, stageCount, pathID)
                self.logger.debug("dstIP:{0}; stageCount:{1}".format(
                    dstIP, stageCount))
                #  (('failureNPoPID', (0, 3, (7,))), ('repairMethod', 'increaseBackupPathPrioriy')):
                #       [[(0, 1), (0, 6), (0, 2), (0, 10002)], [(1, 10002), (1, 2), (1, 4), (1, 1)]]
                if PICA8_VIRTUAL_BRIDGE and idx == len(backupPath)-1:
                    mergeSwitchID = self._getMergedSwitchIDInPrimaryPath4PSFC(key, primaryFP, backupPath)
                    self.logger.debug("mergeSwitchID {0}".format(mergeSwitchID))
                    segPath.append((segPath[0][0], mergeSwitchID))
                for i in range(len(segPath)-1):
                    currentSwitchID = segPath[i][1]
                    if currentSwitchID >= SERVERID_OFFSET:
                        continue
                    else:
                        if i != 0:
                            prevNodeID = segPath[i-1][1]
                        else:
                            prevNodeID = self._getPSFCPathSrcNodeID(primaryFP, key)
                    inPortIndex = self._getInputPortOfDstNode(sfci, direction,
                                                    prevNodeID, currentSwitchID)
                    self.logger.debug(
                        "inPortIndex:{0} prevNodeID:{1}, currentSwitchID:{2}".format(
                            inPortIndex, prevNodeID, currentSwitchID))
                    nextNodeID = segPath[i+1][1]
                    self._installRouteOnPSFCPath(sfci, direction, key,
                        currentSwitchID, nextNodeID, inPortIndex, dstIP)
                stageCount = stageCount + 1

    def _getMergedSwitchIDInPrimaryPath4PSFC(self, key, primaryFP, backupFP):
        (stageCount, switchID, Xp) = key[0][1]
        self.logger.warning(key[0][1])
        self.logger.debug("primaryFP: {0}".format(primaryFP))
        self.logger.debug("stageCount: {0}".format(stageCount))
        self.logger.debug("len of backupFP: {0}".format(backupFP))
        return primaryFP[stageCount+len(backupFP)-1][-1][1]

    def _getPSFCPathSrcNodeID(self, primaryFP, key):
        keyDict = self._parseBackupPathKey(key)
        (vnfLayerNum, bp, Xp) = keyDict["failureNPoPID"]
        return primaryFP[vnfLayerNum][0][1]

    def _installRouteOnPSFCPath(self, sfci, direction, key, currentDpid,
                                    nextDpid, inPortIndex, dstIP,
                                    priority=LOWER_BACKUP_ENTRY_PRIORITY):
        self.logger.debug("_installRouteOnPSFCPath")
        self.logger.info("currentDpid:{0}".format(currentDpid))
        datapath = self.dpset.get(int(str(currentDpid), 0))
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        matchFields={
            'in_port': inPortIndex,
            'eth_type': ether_types.ETH_TYPE_IP,
            'ipv4_dst': dstIP+"/32"}
        match = parser.OFPMatch(**matchFields)

        # get default src/dst ether and default OutPort
        (srcMAC, dstMAC, defaultOutPort) = self._getNextHopActionFields(
                                    sfci, direction, currentDpid, nextDpid)
        if defaultOutPort == None:
            raise ValueError("PSFC: can not get default out port")
        self.logger.debug(
            "srcMAC:{0}, dstMAC:{1}, outport:{2}".format(
                srcMAC, dstMAC, defaultOutPort))
        actions = [
            parser.OFPActionSetField(eth_src=srcMAC),
            parser.OFPActionSetField(eth_dst=dstMAC),
            parser.OFPActionOutput(defaultOutPort)
        ]
        inst = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                actions),
        ]

        self.logger.debug("Add_flow with priority:{0}".format(priority))
        self._add_flow(datapath, match, inst,
                        table_id=MAIN_TABLE,
                        priority=priority)
        self.pSFCIbm.addSFCIPSFCFlowTableEntry(sfci.sfciID, key, currentDpid,
                                            MAIN_TABLE, matchFields,
                                            actions, inst, priority)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _switchFeaturesHandler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id

        # install table-miss flow entry in MAIN_TABLE
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.

    @set_ev_cls(event.EventSwitchLeave)
    def _delSwitchHandler(self, ev):
        switch = ev.switch
        switchID = switch.dp.id
        self._pSFCHandleNodeFailure(switchID)

    # @set_ev_cls(event.EventLinkDelete)
    # def _delLinkHandler(self, ev):
    #     link = ev.link
    #     # TODO: implement link failure in the future

    def _sendCmdRply(self, cmdID, cmdState):
        cmdRply = CommandReply(cmdID, cmdState)
        cmdRply.attributes["source"] = {"ryu notVia-pSFC"}
        rplyMsg = SAMMessage(MSG_TYPE_NETWORK_CONTROLLER_CMD_REPLY, cmdRply)
        queue = MEDIATOR_QUEUE
        self._messageAgent.sendMsg(queue, rplyMsg)

    def _delSFCIHandler(self, cmd):
        self.logger.info('*** notVia-pSFC App Received command={0}'.format(cmd))
        try:
            sfc = cmd.attributes['sfc']
            sfci = cmd.attributes['sfci']
            # TODO: delete route
            # self._delSFCIRoute(sfc, sfci)
            self._sendCmdRply(cmd.cmdID,CMD_STATE_SUCCESSFUL)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                "notVia-pSFC _delSFCIHandler")
            self._sendCmdRply(cmd.cmdID, CMD_STATE_FAIL)
