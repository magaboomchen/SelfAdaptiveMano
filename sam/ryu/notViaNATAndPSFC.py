#!/usr/bin/python
# -*- coding: UTF-8 -*-

from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib.packet import ether_types
from ryu.topology import event

from sam.ryu.conf.ryuConf import MAIN_TABLE, PICA8_VIRTUAL_BRIDGE
from sam.ryu.notViaNATIBMaintainer import NotViaNATIBMaintainer
from sam.ryu.pSFCIBMaintainer import PSFCIBMaintainer, LOWER_BACKUP_ENTRY_PRIORITY, \
    UPPER_BACKUP_ENTRY_PRIORITY
from sam.ryu.frr import FRR
from sam.base.messageAgent import SAMMessage, MEDIATOR_QUEUE, MSG_TYPE_NETWORK_CONTROLLER_CMD_REPLY
from sam.base.command import CMD_STATE_SUCCESSFUL, CMD_STATE_FAIL, CommandReply
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.serverController.serverManager.serverManager import SERVERID_OFFSET


class NotViaNATAndPSFC(FRR):
    # OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    # _CONTEXTS = {
    #     'dpset': dpset.DPSet,
    #     'TopoCollector': TopoCollector
    #     }

    def __init__(self, *args, **kwargs):
        super(NotViaNATAndPSFC, self).__init__(*args, **kwargs)
        logConfigur = LoggerConfigurator(__name__, './log',
                                        'notViaNATAndPSFC.log', level='info')
        self.logger = logConfigur.getLogger()
        self.logger.info("Initialize NotViaNATAndPSFC App !")
        self.ibm = NotViaNATIBMaintainer()
        self.pSFCIbm = PSFCIBMaintainer()
        self.logger.info("NotViaNATAndPSFC App is running !")

    def _addSFCHandler(self, cmd):
        self.logger.debug(
            '*** NotViaNATAndPSFC App Received command={0}'.format(cmd))
        try:
            sfc = cmd.attributes['sfc']
            self.logger.info("add sfc: {0}".format(sfc.sfcUUID))
            self._addRoute2Classifier(sfc)
            self._sendCmdRply(cmd.cmdID, CMD_STATE_SUCCESSFUL)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                "Ryu app NotViaNATAndPSFC _addSFCHandler ")
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
                "Ryu app NotViaNATAndPSFC _serverStatusChangeHandler ")
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
        # self.logger.warning("sfciID is {0}".format(sfciID))
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
                self.logger.warning("actions is {0}".format(actions))
                # TODO: hard code, please judge actions' type, e.g. outport or group
                outPort = actions[-1].port
                inst = entry["inst"]
                if priority == LOWER_BACKUP_ENTRY_PRIORITY:
                    # self.logger.debug(
                    #     "_del_flow dpid:{0}, match:{1}, priority:{2}".format(
                    #         dpid, match, priority))
                    # self._del_flow(datapath, match, tableID, priority, outPort=outPort)
                    # self.syncDatapath(datapath)

                    # # delete primary path route entry
                    # self._del_flow(datapath, match, tableID)
                    # self.syncDatapath(datapath)

                    self._add_flow(datapath, match, inst, tableID,
                                    priority=UPPER_BACKUP_ENTRY_PRIORITY)
                    self.syncDatapath(datapath)
                    priority = UPPER_BACKUP_ENTRY_PRIORITY

    def _addSFCIHandler(self, cmd):
        self.logger.debug(
            '*** NotViaNATAndPSFC App Received command={0}'.format(cmd))
        try:
            sfc = cmd.attributes['sfc']
            sfci = cmd.attributes['sfci']
            self.logger.info("add sfci: {0}".format(sfci.sfciID))
            self._addSFCIRoute(sfc, sfci)
            self.pSFCIbm.addSFCI(sfci)
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
            # self._installBackupPaths(sfci, direction)

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

                self._addNotViaSFCIGroupTable(currentSwitchID,
                    nextNodeID, sfci, direction, stageCount, groupID)
                self._addNotViaSFCIFlowtable(currentSwitchID,
                    sfci.sfciID, inPortIndex, dstIP, groupID)

    def _addNotViaSFCIGroupTable(self, currentDpid, nextDpid, sfci,
                                    direction, stageCount, groupID):
        datapath = self.dpset.get(int(str(currentDpid), 0))
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        buckets = []
        # get default src/dst ether and default OutPort
        (srcMAC, dstMAC, defaultOutPort) \
            = self._getNextHopActionFields(sfci, direction, currentDpid,
                                            nextDpid)
        if defaultOutPort == None:
            raise ValueError("NotViaNATAndPSFC: can not get default out port")
        self.logger.debug("Bucket1")
        self.logger.debug("srcMAC:{0},dstMAC:{1},"
            "outport:{2}".format(srcMAC, dstMAC, defaultOutPort))
        actions = [
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
        self.logger.warning("backupPaths.keys(): {0}".format(backupPaths.keys()))
        for key in backupPaths.keys():
            self.logger.warning("key: {0}".format(key))
            if self._isPSFCBackupPath(key):
                continue
            (repairSwitchID, failureNodeID, newPathID) \
                = self._getRepairSwitchIDAndFailureNodeIDAndNewPathIDFromKey(key)
            if repairSwitchID == currentDpid and failureNodeID == nextDpid:
                self.logger.info("_getNewDstIP")
                return self.getSFCIStageDstIP(sfci, stageCount, newPathID)
        else:
            return None

    def _addNotViaSFCIFlowtable(self, currentDpid, sfciID, inPortIndex, dstIP, groupID):
        self.logger.debug("_addNotViaSFCIFlowtable")
        datapath = self.dpset.get(int(str(currentDpid),0))
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        matchFields = {
            'in_port': inPortIndex,
            'eth_type':ether_types.ETH_TYPE_IP,
            'ipv4_dst':dstIP}
        match = parser.OFPMatch(**matchFields)

        actions = [parser.OFPActionGroup(groupID)]
        inst = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)
        ]
        self._add_flow(datapath, match, inst,
                        table_id=MAIN_TABLE, priority=3)
        self.ibm.addSFCIFlowTableEntry(sfciID, currentDpid,
                                        MAIN_TABLE, matchFields, groupID)

    def _installBackupPaths(self, sfci, direction):
        primaryPathID = self._getPathID(direction["ID"])
        primaryFP = self._getPrimaryPath(sfci, primaryPathID)
        backupFPs = self._getBackupPaths(sfci, primaryPathID)
        for key, backupPath in backupFPs.items():
            if self._isPSFCBackupPath(key):
                continue
            # if self._isAbandonBackupPath(key):
            #     continue
            pathID = self._getNewPathID4Key(key)
            stageCount = self._getStageCount4Key(key)
            self.logger.debug("_installBackupPaths:{0}".format(backupPath))
            for segPath in backupPath:
                if self._isInnerNFVISegPath(segPath):
                    # SFF inner routing
                    continue
                dstIP = self.getSFCIStageDstIP(sfci, stageCount, pathID)
                self.logger.debug("dstIP:{0}; stageCount:{1}".format(
                                    dstIP, stageCount))
                for i in range(1, len(segPath)-1):
                    prevNodeID = segPath[i-1][1]
                    currentSwitchID = segPath[i][1]
                    nextNodeID = segPath[i+1][1]
                    inPortIndex = self._getInputPortOfDstNode(sfci, direction,
                                                                prevNodeID, currentSwitchID)
                    self.logger.debug(
                        "inPortIndex:{0} prevNodeID:{1}, currentSwitchID:{2}".format(
                            inPortIndex, prevNodeID, currentSwitchID))
                    self._installRouteOnBackupPath(sfci, direction,
                        currentSwitchID, nextNodeID, inPortIndex, dstIP)
                    if i == len(segPath)-2:
                        nextDpidOnPrimaryFP \
                            = self._getNotViaByPassPathLastNodesNextDpid(
                                key, primaryFP)
                        inPortIndex = self._getInputPortOfDstNode(sfci, direction,
                                                        currentSwitchID, nextNodeID)
                        self._installLastRouteOnBackupPath(sfci, direction,
                                                            nextNodeID, nextDpidOnPrimaryFP,
                                                            inPortIndex, dstIP, stageCount,
                                                            primaryPathID)

    # def _isAbandonBackupPath(self, key):
    #     if key[0] not in [('failureLayerNodeID', (0, 4))]:
    #         return True
    #     else:
    #         return False

    def _getStageCount4Key(self, key):
        keyDict = self._parseBackupPathKey(key)
        if "repairLayerSwitchID" in keyDict.keys():
            (layerNum, repairSwitchID) = keyDict["repairLayerSwitchID"]
        elif "failureNPoPID" in keyDict.keys():
            (layerNum, bp, xp) = keyDict["failureNPoPID"]
        else:
            layerNum = None
        return layerNum

    def _installRouteOnBackupPath(self, sfci, direction, currentDpid,
                                    nextDpid, inPortIndex, dstIP, priority=3):
        self.logger.debug("_installRouteOnBackupPath")
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
            raise ValueError("NotViaNATAndPSFC: can not get default out port")
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
                actions)
        ]

        self.logger.debug("Add_flow with priority:{0}".format(priority))
        self._add_flow(datapath, match, inst, table_id=MAIN_TABLE,
                        priority=priority)
        self.ibm.addSFCIFlowTableEntry(sfci.sfciID, currentDpid,
                                        MAIN_TABLE, matchFields)

    def _getNotViaByPassPathLastNodesNextDpid(self, key, primaryFP):
        keyDict = self._parseBackupPathKey(key)
        if "mergeLayerSwitchID" not in keyDict.keys():
            return None
        else:
            (layerNum, mergeNodeID) = keyDict["mergeLayerSwitchID"]
        segPath = primaryFP[layerNum]
        for nodeIndex in range(len(segPath)-1):
            (layerNum, nodeID) = segPath[nodeIndex]
            if nodeID == mergeNodeID:
                return segPath[nodeIndex+1][1]
        else:
            return None

    def _installLastRouteOnBackupPath(self, sfci, direction,
                                        currentDpid, nextDpidOnPrimaryPath,
                                        inPortIndex,
                                        dstIP, stageCount, primaryPathID):
        self.logger.debug("_installLastRouteOnBackupPath")
        self.logger.debug("in_port:{0}, dstIP:{1}, currentDpid:{2}".format(
                            inPortIndex, dstIP, currentDpid))
        datapath = self.dpset.get(int(str(currentDpid), 0))
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        matchFields={
            'in_port': inPortIndex,
            'eth_type':ether_types.ETH_TYPE_IP,
            'ipv4_dst': dstIP+"/32"}
        match = parser.OFPMatch(**matchFields)

        # get default src/dst ether and default OutPort
        (srcMAC, dstMAC, defaultOutPort) = self._getNextHopActionFields(
            sfci, direction, currentDpid, nextDpidOnPrimaryPath)
        newDstIP = self.getSFCIStageDstIP(sfci, stageCount, primaryPathID)
        if defaultOutPort == None:
            raise ValueError("UFRR: can not get default out port")
        self.logger.info(
            "srcMAC:{0}, dstMAC:{1}, outport:{2}".format(
                srcMAC, dstMAC, defaultOutPort))
        actions = [
            parser.OFPActionSetField(eth_src=srcMAC),
            parser.OFPActionSetField(eth_dst=dstMAC),
            parser.OFPActionSetField(ipv4_dst=newDstIP),
            parser.OFPActionOutput(defaultOutPort)
        ]

        inst = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                actions)
        ]

        # WARNINGS! We find that OvS doesn't support MPLS POP following a goto table.
        # Flow doesn't match the entry in MAIN_TABLE
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

        self._add_flow(datapath, match, inst, table_id=MAIN_TABLE, priority=3)
        self.ibm.addSFCIFlowTableEntry(sfci.sfciID, currentDpid,
                        MAIN_TABLE, matchFields)

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
            raise ValueError("NotViaNATAndPSFC: can not get default out port")
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
        # We don't install this route actually.
        # self._add_flow(datapath, match, inst,
        #                 table_id=MAIN_TABLE,
        #                 priority=priority)
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
