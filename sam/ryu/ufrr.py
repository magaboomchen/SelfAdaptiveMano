#!/usr/bin/python
# -*- coding: UTF-8 -*-

from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3, ofproto_v1_4

from ryu.lib.packet import ether_types
from ryu.base.app_manager import lookup_service_brick

from sam.ryu.conf.ryuConf import MAIN_TABLE
from sam.ryu.ufrrIBMaintainer import UFRRIBMaintainer
from sam.ryu.frr import FRR
from sam.base.messageAgent import SAMMessage, MSG_TYPE_NETWORK_CONTROLLER_CMD_REPLY, MEDIATOR_QUEUE
from sam.base.command import CommandReply, CMD_STATE_SUCCESSFUL, CMD_STATE_FAIL
from sam.base.sshAgent import SSHAgent
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.loggerConfigurator import LoggerConfigurator


class UFRR(FRR):
    def __init__(self, *args, **kwargs):
        super(UFRR, self).__init__(*args, **kwargs)
        logConfigur = LoggerConfigurator(__name__, './log', 'ufrr.log', level='info')
        self.logger = logConfigur.getLogger()
        self.logger.info("Initialize UFRR App !")
        self.ibm = UFRRIBMaintainer()
        self.logger.info("UFRR App is running !")
        self.L2 = lookup_service_brick('L2')
        self._initSSHAgentDict()

    def _initSSHAgentDict(self):
        self.sshAgentsDict = {}
        for dpid in self._switchConfs:
            remoteIP = self._getPhysicalSwitchManagementIP(dpid)
            sshUsrname = self._getPhysicalSwitchUserName(dpid)
            sshPassword = self._getPhysicalSwitchPassword(dpid)
            self.sshAgentsDict[sshUsrname, sshPassword, remoteIP] = SSHAgent()
            self.sshAgentsDict[sshUsrname, sshPassword, remoteIP].connectSSH(sshUsrname, sshPassword, remoteIP)

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
                "Ryu app UFRR _addSFCHandler ")
            self._sendCmdRply(cmd.cmdID, CMD_STATE_FAIL)
        finally:
            pass

    def _serverStatusChangeHandler(self, cmd):
        # self.logger.debug(
        #     "*** FRR App Received server status change"
        #     " command={0}".format(cmd))
        try:
            serverDownList = cmd.attributes['serverDown']
            self._shutdownServersPort(serverDownList)
            # TODO: process serverUp in the future
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                "Ryu app UFRR _serverStatusChangeHandler ")
        finally:
            pass

    def _shutdownServersPort(self, serverDownList):
        for server in serverDownList:
            datapathNICMAC = server.getDatapathNICMac().lower()
            # self.logger.debug("server:{0}".format(server))
            dpid = self.L2.getConnectedSwitchDpidByServerMac(datapathNICMAC)
            portID = self.L2.getLocalPortIDByMac(datapathNICMAC)
            self._shutdownSwitchPort(dpid, portID)

    def _shutdownSwitchPort(self, dpid, portID):
        # shutdown port by ssh and ovs-ofctl command!
        # self.logger.debug("shutdown switch:{0}'s port:{1}".format(dpid, portID))
        remoteIP = self._getPhysicalSwitchManagementIP(dpid)
        sshUsrname = self._getPhysicalSwitchUserName(dpid)
        sshPassword = self._getPhysicalSwitchPassword(dpid)
        # self.logger.debug("remoteIP: {0}, usrName: {1}, password: {2}".format(remoteIP, sshUsrname, sshPassword))
        # self.sshAgent.connectSSH(sshUsrname, sshPassword, remoteIP)
        portName = self._getPortName(dpid, portID)
        command = "/ovs/bin/ovs-ofctl mod-port br{0} {1} down".format(dpid, portName)
        # self.logger.debug("command is {0}".format(command))
        # rv = self.sshAgent.runShellCommand(command)
        if (sshUsrname, sshPassword, remoteIP) not in self.sshAgentsDict:
            self.sshAgentsDict[sshUsrname, sshPassword, remoteIP] = SSHAgent()
            self.sshAgentsDict[sshUsrname, sshPassword, remoteIP].connectSSH(sshUsrname, sshPassword, remoteIP)
        rv = self.sshAgentsDict[sshUsrname, sshPassword, remoteIP].runShellCommand(command)
        stdin = rv['stdout'].read().decode('utf-8')
        stdout = rv['stderr'].read().decode('utf-8')
        # self.logger.debug("stdout: {0} stderr: {1}".format(stdin, stdout))
        # self.sshAgent.disconnectSSH()
        self.sshAgentsDict[sshUsrname, sshPassword, remoteIP].disconnectSSH()
        del self.sshAgentsDict[sshUsrname, sshPassword, remoteIP]
        self.sshAgentsDict.pop((sshUsrname, sshPassword, remoteIP), None)
        self.logger.debug("shutdown message sent!")

    def _getPortName(self, dpid, portID):
        if portID >= 49:
            portType = 't'
        else:
            portType = 'g'
        return "{0}e-1/1/{1}".format(portType, portID)

    def _shutdownSwitchPortByOpenFlowProtocol(self, dpid, portID):
        # reference
        # https://github.com/faucetsdn/ryu/blob/master/ryu/lib/stplib.py
        self.logger.debug("shutdown switch:{0}'s port:{1}".format(
                                                        dpid, portID))
        datapath = self.dpset.get(int(str(dpid), 0))

        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        hw_addr = self.L2.getMacByLocalPort(dpid, portID)
        self.logger.debug("corresponding switch port's hw_addr:{0}".format(hw_addr))

        config = ofp.OFPPC_PORT_DOWN | ofp.OFPPC_NO_RECV | ofp.OFPPC_NO_FWD | ofp.OFPPC_NO_PACKET_IN

        advertise = (ofp.OFPPF_10MB_HD | ofp.OFPPF_100MB_FD |
                        ofp.OFPPF_1GB_FD | ofp.OFPPF_COPPER |
                        ofp.OFPPF_AUTONEG | ofp.OFPPF_PAUSE |
                        ofp.OFPPF_PAUSE_ASYM)
        if ofp.OFP_VERSION == ofproto_v1_3.OFP_VERSION:
            # https://ryu.readthedocs.io/en/latest/ofproto_v1_3_ref.html
            # mask = 0b1100101
            mask = (ofp.OFPPC_PORT_DOWN | ofp.OFPPC_NO_RECV |
                    ofp.OFPPC_NO_FWD | ofp.OFPPC_NO_PACKET_IN)
            req = ofp_parser.OFPPortMod(datapath, portID, hw_addr, config,
                                        mask, advertise)
        elif ofp.OFP_VERSION == ofproto_v1_4.OFP_VERSION:
            # https://ryu.readthedocs.io/en/latest/ofproto_v1_4_ref.html
            mask = (ofp.OFPPC_PORT_DOWN | ofp.OFPPC_NO_RECV |
                    ofp.OFPPC_NO_FWD | ofp.OFPPC_NO_PACKET_IN)
            advertise = (ofp.OFPPF_10MB_HD | ofp.OFPPF_100MB_FD |
                        ofp.OFPPF_1GB_FD | ofp.OFPPF_COPPER |
                        ofp.OFPPF_AUTONEG | ofp.OFPPF_PAUSE |
                        ofp.OFPPF_PAUSE_ASYM)
            properties = [ofp_parser.OFPPortModPropEthernet(advertise)]
            req = ofp_parser.OFPPortMod(datapath, portID, hw_addr, config,
                                        mask, properties)
        else:
            raise ValueError("Unknown ofp version:{0}".format(ofp))
        datapath.send_msg(req)
        self.logger.debug("shutdown message sent!")

    def _addSFCIHandler(self, cmd):
        self.logger.debug(
            '*** FRR App Received command={0}'.format(cmd))
        try:
            sfc = cmd.attributes['sfc']
            sfci = cmd.attributes['sfci']
            self.logger.info("add sfci: {0}".format(sfci.sfciID))
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
                prevNodeID = segPath[i-1][1]
                currentSwitchID = segPath[i][1]
                inPortIndex = self._getInputPortOfDstNode(sfci, direction,
                                                prevNodeID, currentSwitchID)
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
                    sfci, stageCount, primaryPathID, inPortIndex, dstIP, groupID)

    def _addUFRRSFCIGroupTable(self, currentDpid, nextDpid, sfci,
                                direction, stageCount, groupID):
        datapath = self.dpset.get(int(str(currentDpid), 0))
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
                parser.OFPActionSetField(eth_src=srcMAC),
                parser.OFPActionSetField(eth_dst=dstMAC),
                parser.OFPActionSetField(ipv4_dst=newDstIP),
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
                                pathID, inPortIndex, dstIP, groupID):
        self.logger.info("_addUFRRSFCIFlowtable")
        sfciID = sfci.sfciID
        datapath = self.dpset.get(int(str(currentDpid),0))
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        matchFields = {
                        'in_port': inPortIndex,
                        'eth_type': ether_types.ETH_TYPE_IP,
                        'ipv4_dst': dstIP}
        match = parser.OFPMatch(**matchFields)

        actions = [
            parser.OFPActionGroup(groupID)
        ]
        inst = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)
        ]
        self._add_flow(datapath, match, inst, table_id=MAIN_TABLE,
                        priority=3)
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
                    prevNodeID = segPath[i-1][1]
                    currentSwitchID = segPath[i][1]
                    nextNodeID = segPath[i+1][1]
                    inPortIndex = self._getInputPortOfDstNode(sfci, direction,
                                                    prevNodeID, currentSwitchID)
                    self._installRouteOnBackupPath(sfci, direction,
                        currentSwitchID, nextNodeID, inPortIndex, dstIP, pathID,
                        stageCount)

    def _getNewPathIDFromKey(self, key):
        keyDict = self._parseBackupPathKey(key)
        if "newPathID" in keyDict.keys():
            return keyDict["newPathID"]
        else:
            raise ValueError("Unknown key")

    def _installRouteOnBackupPath(self, sfci, direction, currentDpid,
            nextDpid, inPortIndex, dstIP, pathID, stageCount):
        self.logger.info("_installRouteOnBackupPath")
        self.logger.info("currentDpid:{0}".format(currentDpid))
        datapath = self.dpset.get(int(str(currentDpid), 0))
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        matchFields={   
                        'in_port': inPortIndex,
                        'eth_type':ether_types.ETH_TYPE_IP,
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
            parser.OFPActionSetField(eth_src=srcMAC),
            parser.OFPActionSetField(eth_dst=dstMAC),
            parser.OFPActionOutput(defaultOutPort)
        ]

        inst = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                actions)
        ]

        self.logger.debug("_installRouteOnBackupPath Add_flow")
        self._add_flow(datapath, match, inst, table_id=MAIN_TABLE,
                        priority=3)
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

    def _sendCmdRply(self, cmdID, cmdState):
        cmdRply = CommandReply(cmdID,cmdState)
        cmdRply.attributes["source"] = {"ryu uffr"}
        rplyMsg = SAMMessage(MSG_TYPE_NETWORK_CONTROLLER_CMD_REPLY,cmdRply)
        queue = MEDIATOR_QUEUE
        self._messageAgent.sendMsg(queue,rplyMsg)

    def _delSFCIHandler(self, cmd):
        self.logger.info('*** ufrr App Received command={0}'.format(cmd))
        try:
            sfc = cmd.attributes['sfc']
            sfci = cmd.attributes['sfci']
            # TODO: delete route
            # self._delSFCIRoute(sfc, sfci)
            self._sendCmdRply(cmd.cmdID,CMD_STATE_SUCCESSFUL)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                "ufrr _delSFCIHandler")
            self._sendCmdRply(cmd.cmdID, CMD_STATE_FAIL)
