#!/usr/bin/python
# -*- coding: UTF-8 -*-

import copy
import time

from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.controller import dpset
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ipv4
from ryu.lib.packet import arp
from ryu.lib.packet import ether_types
from ryu.topology import switches
from ryu.base.app_manager import *

from sam.ryu.conf.ryuConf import *
from sam.ryu.topoCollector import TopoCollector, TopologyChangeEvent
from sam.ryu.datapathStateSynchronizer import DatapathStateSynchronizer
from sam.ryu.baseApp import BaseApp
from sam.ryu.conf.ryuConf import DCNGATEWAY_INBOUND_PORT, ARP_TIMEOUT
from sam.base.messageAgent import *
from sam.base.command import *
from sam.base.path import *
from sam.base.socketConverter import *
from sam.base.vnf import *
from sam.serverController.serverManager.serverManager import *
from sam.base.exceptionProcessor import ExceptionProcessor


class FRR(BaseApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {
        'dpset': dpset.DPSet,
        'TopoCollector': TopoCollector,
        'DatapathStateSynchronizer': DatapathStateSynchronizer
        }

    def __init__(self, *args, **kwargs):
        super(FRR, self).__init__(*args, **kwargs)
        self.logger.info("Initialize FRR App !")
        self.dpset = kwargs['dpset']
        self.topoCollector = kwargs['TopoCollector']
        self.dss = kwargs['DatapathStateSynchronizer']
        self.L2 = lookup_service_brick('L2')
        self.wer = lookup_service_brick('WestEastRouting')
        if self.L2 == None or self.wer == None or self.dss == None:
            self.logger.error("FRR service connection error."
                "L2:{0}, wer:{1}, dss:{2} "
                "You may need to sort app's start sequence".format(
                    self.L2, self.wer, self.dss
                ))
            raise ValueError("Can't start frr!")
        self.ibm = None
        self._sc = SocketConverter()
        self._sffType = SOFTWARE_SFF
        self.logger.setLevel(logging.DEBUG)
        self.logger.info("FRR App is running !")

    def _addRoute2Classifier(self, sfc):
        # install route to classifier
        for direction in sfc.directions:
            dpid = self._getSwitchByClassifier(direction['ingress'])
            datapath = self.dpset.get(int(str(dpid), 0))
            source = direction['source']
            if source.has_key("IPv4"):
                ipv4Address = source["IPv4"]
                if ipv4Address in [None, "*", "0.0.0.0"]:
                    inPortIndex = DCNGATEWAY_INBOUND_PORT
                else:
                    inPortIndex = self._getPortbyIP(datapath, source["IPv4"])
                    if inPortIndex == None:
                        raise ValueError("_addRoute2Classifier: invalid source")
            else:
                raise ValueError("_addRoute2Classifier: invalid source")
            classifierMAC = direction['ingress'].getDatapathNICMac()
            classifierIP = direction['ingress'].getDatapathNICIP()
            classifierPort = self._getPortbyIP(datapath, classifierIP)
            self.logger.debug("classifierPort:{0}".format(classifierPort))
            if classifierPort == None:
                raise ValueError("Can't get classifier output port")
            self._installRoute4Switch2Classifier(sfc.sfcUUID,
                datapath, inPortIndex, classifierMAC, classifierPort)

    def _getSwitchByClassifier(self, classifier):
        # dpid = classifier.getServerID()
        self.logger.setLevel(logging.DEBUG)
        self.logger.debug("in _getSwitchByClassifier ")
        datapathNICIP = classifier.getDatapathNICIP()
        self.logger.debug("datapathNICIP:{0}".format(datapathNICIP))
        for dpid in self._switchConfs.keys():
            net = self._getLANNet(dpid)
            self.logger.debug("net:{0}".format(net))
            if self._isLANIP(datapathNICIP, net):
                return dpid
        else:
            raise ValueError("Can not find switch by classifier")

    def _getFirstSwitchIDInSFCI(self, sfci, direction):
        forwardingPathSet = sfci.forwardingPathSet
        primaryForwardingPath = forwardingPathSet.primaryForwardingPath
        directionID = direction["ID"]
        if directionID == 0:
            firstPath = primaryForwardingPath[DIRECTION1_PATHID_OFFSET][0]
        else:
            firstPath = primaryForwardingPath[DIRECTION2_PATHID_OFFSET][0]
        firstSwitchID = firstPath[1]
        # the first node is a server, the second node is a switch
        return firstSwitchID

    # group table set dst port design:
    # ufrr.py use event to request mac-port mapping from
    # _switchesLANMacTable in L2.py.
    # in L2.py, check _switchesLANMacTable, if it unexisted, return None
    # and send arp request.
    # if ufrr get None, time.sleep(ARP_TIMEOUT) then retry again,
    # max try number is ARP_MAX_RETRY_NUM.
    def _getPortbyIP(self, datapath, ipAddress):
        dpid = datapath.id
        maxTryNumber = ARP_MAX_RETRY_NUM
        port = None
        for tryNumber in range(maxTryNumber):
            # get mac by arp table
            dstMac = self.wer.getMacByIp(dpid, ipAddress)
            if dstMac == None:
                self._broadcastArpRequest(datapath,ipAddress)
                time.sleep(ARP_TIMEOUT)
                continue

            # get port by mac table
            port = self.L2.getSwitchLocalPortByMac(dpid, dstMac)
            if port == None:
                continue
        return port

    def _installRoute4Switch2Classifier(self, sfcUUID, datapath, inPortIndex,
                                            classifierMAC, outputPort):
        dpid = datapath.id
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        matchFields={'eth_type':ether_types.ETH_TYPE_IP, 'in_port':inPortIndex}
        match = parser.OFPMatch(**matchFields)
        in_port_info = self.dpset.get_port(dpid, inPortIndex)
        actions = [
            parser.OFPActionSetField(eth_src=in_port_info.hw_addr),
            parser.OFPActionSetField(eth_dst=classifierMAC),
            parser.OFPActionOutput(outputPort)
        ]
        inst = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,actions)
        ]
        self._add_flow(datapath,match,inst,table_id=MAIN_TABLE, priority=4)
        self.ibm.addSFCFlowTableEntry(sfcUUID, dpid,
            MAIN_TABLE, matchFields)

    def getSFCIStageDstIP(self, sfci, stageCount, pathID):
        if stageCount<len(sfci.vnfiSequence):
            vnfID = sfci.getVNFTypeByStageNum(stageCount)
        else:
            vnfID = VNF_TYPE_CLASSIFIER
        sfciID = sfci.sfciID
        ipNum = (10<<24) + ((vnfID & 0xF) << 20) + ((sfciID & 0xFFF) << 8) \
                    + (pathID & 0xFF)
        return self._sc.int2ip(ipNum)

    def _canSkipPrimaryPathFlowInstallation(self, sfciID, dstIP,
                                                currentSwitchID):
        matchFields = {'eth_type':ether_types.ETH_TYPE_IP,
            'ipv4_dst':dstIP}
        if self.ibm.hasSFCIFlowTable(sfciID, currentSwitchID,
            matchFields):
            self.logger.warning("Duplicate Flow Table Entry!")
            return True
        else:
            return False

    def _getPathID(self, directionID):
        if directionID == 0:
            pathID = DIRECTION1_PATHID_OFFSET
        else:
            pathID = DIRECTION2_PATHID_OFFSET
        return pathID

    def _getPrimaryPath(self, sfci, primaryPathID):
        fpSet = sfci.forwardingPathSet
        primaryFPDict = fpSet.primaryForwardingPath
        if primaryPathID in primaryFPDict.keys():
            primaryFP = primaryFPDict[primaryPathID]
        else:
            primaryFP = None
        return primaryFP

    def _getSrcDstServerInStage(self, stage):
        srcServerID = stage[0][1]
        dstServerID = stage[-1][1]
        return (srcServerID,dstServerID)

    def _getBackupNextHop(self, currentDpid, nextDpid, 
                            sfci, direction, stageCount):
        primaryPathID = self._getPathID(direction["ID"])
        backupPaths = self._getBackupPaths(sfci,primaryPathID)
        for key in backupPaths.iterkeys():
            if self._isThisBackupPathProtectsNextHop(key, currentDpid,
                    nextDpid, stageCount):
                return backupPaths[key][0][1][1]
        else:
            return None

    def _isThisBackupPathProtectsNextHop(self, key, currentDpid,
                                            nextDpid, stageCount):
        if key[0][0] == "failureNPoPID":
            # pSFC
            # ("failureNPoPID", (vnfLayerNum, bp, Xp)),
            # ("repairMethod", "increaseBackupPathPrioriy")
            return False
        elif key[0][0] == "failureLayerNodeID":
            # node protection frr
            # ("failureLayerNodeID", abandonLayerNodeID),
            # ("repairMethod", "fast-reroute"),
            # ("repairLayerSwitchID", (stageNum, startLayerNodeID[1])),
            # ("mergeLayerSwitchID", (stageNum, endLayerNodeID[1])),
            # ("newPathID", pathID)
            layerNum = key[2][1][0]
            repairSwitchID = key[2][1][1]
            failureNodeID = key[0][1][1]
            if (currentDpid == repairSwitchID 
                    and nextDpid == failureNodeID
                    and stageCount == layerNum):
                return True
            else:
                return False
        elif key[0][0] == 'failureNodeID':
            # (('failureNodeID', 2), ('repairMethod', 'fast-reroute'),
            # ('repairSwitchID', 1), ('newPathID', 2))
            repairSwitchID = key[2][1]
            failureNodeID = key[0][1]
            if (currentDpid == repairSwitchID 
                    and nextDpid == failureNodeID):
                return True
            else:
                return False
        elif key[0][0] == "failureLinkID":
            # link protection frr
            raise ValueError("Please implement link protection")
        else:
            raise ValueError("Unknown backup path key:{0}".format(key))

    def _parseBackupPathKey(self, key):
        return dict((x, y) for x, y in key)

    def _getRepairSwitchIDAndFailureNodeIDAndNewPathIDFromKey(self, key):
        # TODO: replace this function by _parseBackupPathKey() which return
        # a dictionary in the future
        if key[0][0] == "failureNPoPID":
            # pSFC
            # ("failureNPoPID", (vnfLayerNum, bp, Xp)),
            # ("repairMethod", "increaseBackupPathPrioriy")
            return False
        elif key[0][0] == "failureLayerNodeID":
            # node protection frr
            # ("failureLayerNodeID", abandonLayerNodeID),
            # ("repairMethod", "fast-reroute"),
            # ("repairLayerSwitchID", (stageNum, startLayerNodeID[1])),
            # ("mergeLayerSwitchID", (stageNum, endLayerNodeID[1])),
            # ("newPathID", pathID)
            layerNum = key[2][1][0]
            repairSwitchID = key[2][1][1]
            failureNodeID = key[0][1][1]
            newPathID = key[4][1]
            return (repairSwitchID, failureNodeID, newPathID)
        elif key[0][0] == 'failureNodeID':
            # (('failureNodeID', 2), ('repairMethod', 'fast-reroute'),
            # ('repairSwitchID', 1), ('newPathID', 2))
            repairSwitchID = key[2][1]
            failureNodeID = key[0][1]
            newPathID = key[3][1]
            return (repairSwitchID, failureNodeID, newPathID)
        elif key[0][0] == "failureLinkID":
            # link protection frr
            raise ValueError("Please implement link protection")
        else:
            raise ValueError("Unknown backup path key:{0}".format(key))

    def _isPSFCBackupPath(self, key):
        if key[0][0] == "failureNPoPID":
            return True
        else:
            return False

    def isFirstElementUnderProtection(self,currentDpid, nextDpid, sfci,
            direction, currentStageCount):
        self.logger.debug("isFirstElementUnderProtection")
        self.logger.debug(
            "currentDpid:{0}, nextDpid:{1}, currentStageCount:{2}".format(
            currentDpid, nextDpid, currentStageCount))
        primaryPathID = self._getPathID(direction["ID"])
        primaryFP = self._getPrimaryPath(sfci,primaryPathID)
        stageCount = -1
        for stage in primaryFP:
            stageCount = stageCount + 1
            if len(stage)==2:
                # SFF inner routing
                continue
            for i in range(len(stage)-1):
                currentSwitchID = stage[i]
                nextNodeID = stage[i+1]
                self.logger.debug(
                    "currentSwitchID:{0}, nextNodeID:{1}, stageCount:{2}".format(
                        currentSwitchID, nextNodeID, stageCount
                    )
                    )
                if currentDpid != currentSwitchID or\
                    nextNodeID != nextDpid:
                    continue
                self.logger.debug(
                    "currentStageCount:{0}, stageCount:{1}".format(
                        currentStageCount,stageCount
                    )
                )
                if currentStageCount == stageCount:
                    return True
                else:
                    return False
        return False

    def _isInnerNFVISegPath(self, segPath):
        if self._sffType == SOFTWARE_SFF:
            if len(segPath) == 3:
                firstNodeID = segPath[0][1]
                secondNodeID = segPath[1][1]
                thirdNodeID = segPath[2][1]
                if (firstNodeID >= SERVERID_OFFSET 
                        and secondNodeID < SERVERID_OFFSET
                        and thirdNodeID >= SERVERID_OFFSET):
                    return True
                else:
                    return False
        elif self._sffType == HARDWARE_SFF:
            return False
        else:
            raise ValueError("Unknown NFVI type")

    def _getNewPathID4Key(self, key):
        if key[0][0] == "failureNPoPID":
            # pSFC
            # ("failureNPoPID", (vnfLayerNum, bp, Xp)),
            # ("repairMethod", "increaseBackupPathPrioriy")
            raise ValueError("no new path ID")
        elif key[0][0] == "failureLayerNodeID":
            # node protection frr
            # ("failureLayerNodeID", abandonLayerNodeID),
            # ("repairMethod", "fast-reroute"),
            # ("repairLayerSwitchID", (stageNum, startLayerNodeID[1])),
            # ("mergeLayerSwitchID", (stageNum, endLayerNodeID[1])),
            # ("newPathID", pathID)
            newPathID = key[4][1]
            return newPathID
        elif key[0][0] == "failureLinkID":
            # link protection frr
            raise ValueError("Please implement link protection")
        else:
            raise ValueError("Unknown backup path key:{0}".format(key))

    def _getBackupPaths(self, sfci, primaryPathID):
        fpSet = sfci.forwardingPathSet
        backupFPDict = fpSet.backupForwardingPath
        if primaryPathID in backupFPDict.keys():
            backupFP = backupFPDict[primaryPathID]
        else:
            backupFP = None
        return backupFP

    def _getNextHopActionFields(self, sfci, direction,
                                    currentDpid, nextDpid):
        self.logger.debug("currentDpid:{0}, nextDpid:{1}".format(currentDpid,
            nextDpid))
        if nextDpid < SERVERID_OFFSET:
            self.logger.debug("_getNextHopActionFields: dst is a switch")
            link = self.topoCollector.links[(currentDpid, nextDpid)]
            srcMAC = link.src.hw_addr
            dstMAC = link.dst.hw_addr
            defaultOutPort = self.L2.getLocalPortByPeerPort(currentDpid,
                                                            nextDpid)
        else:
            self.logger.debug("_getNextHopActionFields: dst is a server")
            server = self.getServerByServerID(sfci, direction, nextDpid)
            dstMAC = server.getDatapathNICMac()
            dstDatapathIP = server.getDatapathNICIP()
            currentDatapath = self.dpset.get(int(str(currentDpid), 0))
            defaultOutPort = self._getPortbyIP(currentDatapath, dstDatapathIP)
            srcMAC = self.L2.getMacByLocalPort(currentDpid, defaultOutPort)
        return (srcMAC, dstMAC, defaultOutPort)

    def _getInputPortOfDstNode(self, sfci, direction, currentDpid, nextDpid):
        self.logger.debug("currentDpid:{0}, nextDpid:{1}".format(currentDpid, nextDpid))
        if currentDpid < SERVERID_OFFSET:
            self.logger.debug("_getInputPortOfDstNode: src is a switch")
            defaultOutPort = self.L2.getLocalPortByPeerPort(nextDpid, currentDpid)
        else:
            self.logger.debug("_getInputPortOfDstNode: src is a server")
            server = self.getServerByServerID(sfci, direction, currentDpid)
            currentDatapathIP = server.getDatapathNICIP()
            nextDatapath = self.dpset.get(int(str(nextDpid), 0))
            defaultOutPort = self._getPortbyIP(nextDatapath, currentDatapathIP)
        return defaultOutPort

    def getServerByServerID(self, sfci, direction, serverID):
        self.logger.debug("getServerByServerID:{0}".format(serverID))
        self.logger.debug("vnfs list: {0}".format(sfci.vnfiSequence))
        for vnf in sfci.vnfiSequence:
            for vnfi in vnf:
                self.logger.debug("vnfi: {0}".format(vnfi))
                node = vnfi.node
                if (isinstance(node, Server) 
                        and node.getServerID() == serverID):
                    return node
        else:
            ingress = direction['ingress']
            egress = direction['egress']
            if ingress.getServerID() == serverID:
                return ingress
            elif egress.getServerID() == serverID:
                return egress
            else:
                self.logger.warning("serverID {0} is None!".format(serverID))
                return None

    def _delSFCIHandler(self, cmd):
        self.logger.info('*** FRR App Received command={0}'.format(cmd))
        try:
            sfc = cmd.attributes['sfc']
            sfci = cmd.attributes['sfci']
            self._delSFCIRoute(sfc, sfci)
            self._sendCmdRply(cmd.cmdID,CMD_STATE_SUCCESSFUL)
            self.ibm.printUIBM()
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                "frr _delSFCIHandler")
            self._sendCmdRply(cmd.cmdID,CMD_STATE_FAIL)

    def _delSFCIRoute(self, sfc, sfci):
        for dpid,entrys in self.ibm.getSFCIFlowTable(sfci.sfciID).items():
            for entry in entrys:
                datapath = self.dpset.get(int(str(dpid), 0))
                parser = datapath.ofproto_parser
                matchFields = entry["matchFields"]
                match = parser.OFPMatch(**matchFields)
                tableID = entry["tableID"]
                self._del_flow(datapath, match, table_id=tableID, priority=2)
                if entry.has_key("groupID"):
                    groupID = entry["groupID"]
                    self._delSFCIGroupTable(datapath, groupID)
                    self.ibm.delGroupID(dpid, groupID)
        self.ibm.delSFCIFlowTableEntry(sfci.sfciID)

    def _delSFCIGroupTable(self, datapath, groupID):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        req = parser.OFPGroupMod(datapath, ofproto.OFPGC_DELETE, 
            ofproto.OFPGT_FF, groupID)
        datapath.send_msg(req)

    def _delSFCHandler(self, cmd):
        self.logger.info('*** FRR App Received command={0}'.format(cmd))
        try:
            sfc = cmd.attributes['sfc']
            self._delRoute2Classifier(sfc)
            self._sendCmdRply(cmd.cmdID, CMD_STATE_SUCCESSFUL)
            self.ibm.printUIBM()
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                "frr _delSFCHandler")
            self._sendCmdRply(cmd.cmdID, CMD_STATE_FAIL)

    def _delRoute2Classifier(self, sfc):
        # delete route to classifier
        for direction in sfc.directions:
            dpid = self._getSwitchByClassifier(direction['ingress'])
            datapath = self.dpset.get(int(str(dpid), 0))
            self._deleteRoute4Switch2Classifier(sfc.sfcUUID, datapath)

    def _deleteRoute4Switch2Classifier(self, sfcUUID, datapath):
        dpid = datapath.id
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        matchFields = self.ibm.getSFCFlowTableEntryMatchFields(sfcUUID,
            dpid, IPV4_CLASSIFIER_TABLE)
        match = parser.OFPMatch(**matchFields)
        # Before delete this route, we must check whether other SFC use the same matchFields.
        count = self.ibm.countSFCRIB(dpid, matchFields)
        if count == 1: # If no, we can delete this route.
            self._del_flow(datapath, match,
                            # table_id=IPV4_CLASSIFIER_TABLE,
                            table_id = MAIN_TABLE,
                            priority = 3)
        else: # If yes, we can't delete this route.
            pass
        self.ibm.delSFCFlowTableEntry(sfcUUID)

    def syncDatapath(self, datapath):
        # pass
        self.dss.sendBarrierRequest(datapath)
        while True:
            if self.dss.getBarrierState(datapath) == True:
                break
            else:
                time.sleep(1/100000.0)
