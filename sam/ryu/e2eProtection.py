#!/usr/bin/python
# -*- coding: UTF-8 -*-

import time

from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib.packet import ether_types
from ryu.topology import event

from sam.ryu.conf.ryuConf import MAIN_TABLE
from sam.ryu.e2eProtectionIBMaintainer import E2EProtectionIBMaintainer, \
    LOWER_BACKUP_ENTRY_PRIORITY, UPPER_BACKUP_ENTRY_PRIORITY, PRIMARY_ENTRY_PRIORITY
from sam.ryu.frr import FRR
from sam.base.messageAgent import SAMMessage, MEDIATOR_QUEUE, MSG_TYPE_NETWORK_CONTROLLER_CMD_REPLY
from sam.base.command import CMD_STATE_SUCCESSFUL, CMD_STATE_FAIL, CommandReply
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.loggerConfigurator import LoggerConfigurator


class E2EProtection(FRR):
    def __init__(self, *args, **kwargs):
        super(E2EProtection, self).__init__(*args, **kwargs)
        logConfigur = LoggerConfigurator(__name__, './log', 'e2eProtection.log', level='debug')
        self.logger = logConfigur.getLogger()
        self.logger.info("Initialize E2EProtection App !")
        self.ibm = E2EProtectionIBMaintainer()
        self.logger.info("E2EProtection App is running !")

    def _addSFCHandler(self, cmd):
        self.logger.debug(
            '*** FRR App Received command={0}'.format(cmd))
        try:
            sfc = cmd.attributes['sfc']
            self.logger.info("add sfc: {0}".format(sfc.sfcUUID))
            self._addRoute2Classifier(sfc)
            self._sendCmdRply(cmd.cmdID, CMD_STATE_SUCCESSFUL)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                "Ryu app E2EProtection _addSFCHandler ")
            self._sendCmdRply(cmd.cmdID, CMD_STATE_FAIL)
        finally:
            pass

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
                "Ryu app NotViaNATAndPSFC _serverStatusChangeHandler ")
        finally:
            pass

    def _tackleServerFailure(self, serverDownList):
        for server in serverDownList:
            serverID = server.getServerID()
            self._e2eProtectionHandleNodeFailure(serverID)

    def getCurrentTimeInMs(self):
        return time.time() * 1000.0

    def _e2eProtectionHandleLinkFailure(self, linkID):
        count = 0
        affectedSFCIIDList \
            = self._getAffectedSFCIIDListByFailureLinkID(linkID)
        for sfciID, primaryPathID in affectedSFCIIDList:
            # for a primary path with primaryPathID, it's corresponding
            # backup path's pathID is primaryPathID+1
            self._increaseSFCIBackupPathPriority(sfciID, primaryPathID+1)
            count = count + 1

        self.end = self.getCurrentTimeInMs()
        self.logger.warning("update {0} entrys in time: {1} ms".format(
            count, str(self.end-self.start)))

    def _getAffectedSFCIIDListByFailureLinkID(self, failureLinkID):
        self.logger.debug("failure link is {0}".format(failureLinkID))
        affectedSFCIIDList = []
        sfciDict = self.ibm.getSFCIDict()
        for sfciID, sfci in sfciDict.items():
            for directionID in [0, 1]:
                primaryPathID = self._getPathID(directionID)
                primaryFP = self._getPrimaryPath(sfci, primaryPathID)
                backupFPs = self._getBackupPaths(sfci, primaryPathID)
                if primaryFP == None or backupFPs == None:
                    continue
                else:
                    self.logger.debug("valid primaryPathID")
                if self._isPathHasFailureLinkID(primaryFP, failureLinkID):
                    affectedSFCIIDList.append((sfciID, primaryPathID))
                    self.logger.debug(
                        "affected sfciID:{0}, primaryPathID:{1}".format(
                            sfciID, primaryPathID))
        return affectedSFCIIDList

    def _e2eProtectionHandleNodeFailure(self, nodeID):
        affectedSFCIIDList \
            = self._getAffectedSFCIIDListByFailureNodeID(nodeID)
        for sfciID, primaryPathID in affectedSFCIIDList:
            # for a primary path with primaryPathID, it's corresponding
            # backup path's pathID is primaryPathID+1
            self._increaseSFCIBackupPathPriority(sfciID, primaryPathID+1)

    def _getAffectedSFCIIDListByFailureNodeID(self, failureNodeID):
        self.logger.debug("failure node is {0}".format(failureNodeID))
        affectedSFCIIDList = []
        sfciDict = self.ibm.getSFCIDict()
        for sfciID, sfci in sfciDict.items():
            for directionID in [0, 1]:
                primaryPathID = self._getPathID(directionID)
                primaryFP = self._getPrimaryPath(sfci, primaryPathID)
                backupFPs = self._getBackupPaths(sfci, primaryPathID)
                if primaryFP == None or backupFPs == None:
                    continue
                else:
                    self.logger.debug("valid primaryPathID")
                if self._isPathHasFailureNodeID(primaryFP, failureNodeID):
                    affectedSFCIIDList.append((sfciID, primaryPathID))
                    self.logger.debug(
                        "affected sfciID:{0}, primaryPathID:{1}".format(
                            sfciID, primaryPathID))
        return affectedSFCIIDList

    def _isPathHasFailureNodeID(self, primaryFP, failureNodeID):
        for segPath in primaryFP:
            for layerNodeID in segPath:
                (layerNum, nodeID) = layerNodeID
                if nodeID == failureNodeID:
                    return True
            else:
                return False

    def _isPathHasFailureLinkID(self, primaryFP, failureLinkID):
        for segPath in primaryFP:
            for index, currentLayerNodeID in enumerate(segPath):
                if index >= len(segPath)-1:
                    continue
                (layerNum, currentNodeID) = currentLayerNodeID
                nextLayerNodeID = segPath[index+1]
                (layerNum, nextNodeID) = nextLayerNodeID
                linkID = (currentNodeID, nextNodeID)
                reverseLinkID = (nextNodeID, currentNodeID)
                if linkID == failureLinkID or reverseLinkID == failureLinkID:
                    return True
            else:
                return False

    def _increaseSFCIBackupPathPriority(self, sfciID, backupPathID):
        self.logger.debug("_increaseSFCIBackupPathPriority,"
                            " sfciID:{0}, backupPathID:{1}".format(sfciID, backupPathID))
        dpidFIBEntryDict \
            = self.ibm.getSFCIFlowTableEntries(sfciID, backupPathID)
        for dpid, entryList in dpidFIBEntryDict.items():
            datapath = self.dpset.get(int(str(dpid), 0))
            for entry in entryList:
                tableID = entry["tableID"]
                matchFields = entry["matchFields"]
                parser = datapath.ofproto_parser
                match = parser.OFPMatch(**matchFields)
                priority = entry["priority"]
                actions = entry["actions"]
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
                    entry["priority"] = UPPER_BACKUP_ENTRY_PRIORITY

    def _addSFCIHandler(self, cmd):
        self.logger.debug(
            '*** FRR App Received command={0}'.format(cmd))
        try:
            sfc = cmd.attributes['sfc']
            sfci = cmd.attributes['sfci']
            self.logger.info("add sfci: {0}".format(sfci.sfciID))
            self._addSFCIRoute(sfc, sfci)
            self.ibm.addSFCI(sfci)
            self._sendCmdRply(cmd.cmdID, CMD_STATE_SUCCESSFUL)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                "Ryu app E2EProtection _addSFCIHandler ")
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
                prevNodeID = segPath[i-1][1]
                currentSwitchID = segPath[i][1]
                inPortIndex = self._getInputPortOfDstNode(sfci, direction,
                                                prevNodeID, currentSwitchID)
                self.logger.info("dpid:{0}".format(currentSwitchID))
                nextNodeID = segPath[i+1][1]

                # if self._canSkipPrimaryPathFlowInstallation(sfci.sfciID,
                #         dstIP, currentSwitchID):
                #     continue

                self._addE2EPSFCIFlowtable(currentSwitchID, nextNodeID,
                                            sfci, direction, primaryPathID,
                                            inPortIndex, 
                                            dstIP, PRIMARY_ENTRY_PRIORITY)

    def _addE2EPSFCIFlowtable(self, currentDpid, nextDpid, 
                                sfci, direction, pathID, 
                                inPortIndex, dstIP, priority):
        self.logger.info("_addE2EPSFCIFlowtable")
        sfciID = sfci.sfciID
        datapath = self.dpset.get(int(str(currentDpid), 0))
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        matchFields = {
            'in_port': inPortIndex,
            'eth_type': ether_types.ETH_TYPE_IP,
            'ipv4_dst': dstIP}
        match = parser.OFPMatch(**matchFields)

        (srcMAC, dstMAC, defaultOutPort) = self._getNextHopActionFields(sfci,
                                            direction, currentDpid, nextDpid)
        if defaultOutPort == None:
            raise ValueError("E2EProtection: can not get default out port")
        self.logger.info("srcMAC:{0}, dstMAC:{1}, outport:{2}".format(
            srcMAC, dstMAC, defaultOutPort))
        actions = [
            parser.OFPActionSetField(eth_src=srcMAC),
            parser.OFPActionSetField(eth_dst=dstMAC),
            parser.OFPActionOutput(defaultOutPort)
        ]
        inst = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)
        ]

        self._add_flow(datapath, match, inst,
                        table_id=MAIN_TABLE, priority=priority)
        self.ibm.addSFCIE2EPFlowTableEntry(
            sfciID, pathID, currentDpid, MAIN_TABLE, matchFields,
            actions, inst, priority=priority
        )

    def _installBackupPaths(self, sfci, direction):
        self.logger.info("_installBackupPaths")
        primaryPathID = self._getPathID(direction["ID"])
        primaryFP = self._getPrimaryPath(sfci, primaryPathID)
        backupFPs = self._getBackupPaths(sfci, primaryPathID)
        for key, backupPath in backupFPs.items():
            stageCount = -1
            for segPath in backupPath:
                stageCount = stageCount + 1
                if self._isInnerNFVISegPath(segPath):
                    # SFF inner routing
                    continue
                dstIP = self.getSFCIStageDstIP(sfci, stageCount, primaryPathID)
                for i in range(1, len(segPath)-1):
                    prevNodeID = segPath[i-1][1]
                    currentSwitchID = segPath[i][1]
                    inPortIndex = self._getInputPortOfDstNode(sfci, direction,
                                                    prevNodeID, currentSwitchID)
                    nextNodeID = segPath[i+1][1]
                    self._addE2EPSFCIFlowtable(currentSwitchID, nextNodeID,
                                                sfci, direction,
                                                primaryPathID+1, inPortIndex, dstIP,
                                                LOWER_BACKUP_ENTRY_PRIORITY)

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

    @set_ev_cls(event.EventSwitchLeave)
    def _delSwitchHandler(self, ev):
        switch = ev.switch
        switchID = switch.dp.id
        self._e2eProtectionHandleNodeFailure(switchID)

    @set_ev_cls(event.EventLinkDelete)
    def _delLinkHandler(self, ev):
        self.start = self.getCurrentTimeInMs()
        link = ev.link
        linkID = (link.src.dpid,link.dst.dpid)
        self.logger.info("delLinkHandler linkID: {0}".format(linkID))
        self._e2eProtectionHandleLinkFailure(linkID)

    # @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    # def _port_status_handler(self, ev):
    #     msg = ev.msg
    #     reason = msg.reason
    #     port_no = msg.desc.port_no
    #     datapath = msg.datapath
    #     dpid = datapath.id
    #     ofproto = datapath.ofproto
    #     port = msg.desc

    #     linkID = self._getAffectedLinkID(dpid, port_no)

    #     if linkID != None and (reason == ofproto.OFPPR_DELETE or reason == ofproto.OFPPR_MODIFY):
    #         self.logger.info("_port_status_handler, dpid: %d, port deleted/modify %s" %(dpid, port_no))
    #         self._e2eProtectionHandleLinkFailure(linkID)

    def _getAffectedLinkID(self, dpid, port_no):
        # for server-switch link, use serverManager's heart beat detection
        return self.topoCollector.getLinkIDByDpidAndPort(dpid, port_no)

    def _sendCmdRply(self, cmdID, cmdState):
        cmdRply = CommandReply(cmdID,cmdState)
        cmdRply.attributes["source"] = {"ryu uffr"}
        rplyMsg = SAMMessage(MSG_TYPE_NETWORK_CONTROLLER_CMD_REPLY, cmdRply)
        queue = MEDIATOR_QUEUE
        self._messageAgent.sendMsg(queue, rplyMsg)

    def _delSFCIHandler(self, cmd):
        self.logger.info('*** e2eP App Received command={0}'.format(cmd))
        try:
            sfc = cmd.attributes['sfc']
            sfci = cmd.attributes['sfci']
            # TODO: delete route
            # self._delSFCIRoute(sfc, sfci)
            self._sendCmdRply(cmd.cmdID,CMD_STATE_SUCCESSFUL)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                "e2eP _delSFCIHandler")
            self._sendCmdRply(cmd.cmdID, CMD_STATE_FAIL)
