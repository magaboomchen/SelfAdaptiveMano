#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid
from typing import List, Tuple, Union

from sam.base.sfc import SFC, SFCI
from sam.orchestration.algorithms.base.pathServerFiller import PathServerFiller
from sam.test.testBase import DCN_GATEWAY_IP
from sam.base.routingMorphic import RoutingMorphic
from sam.base.rateLimiter import RateLimiterConfig
from sam.base.shellProcessor import ShellProcessor
from sam.base.server import SERVER_TYPE_NFVI, Server
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.test.integrate.intTestBase import IntTestBaseClass
from sam.test.fixtures.measurementStub import MeasurementStub
from sam.base.path import DIRECTION0_PATHID_OFFSET, DIRECTION1_PATHID_OFFSET, MAPPING_TYPE_MMLPSFC, ForwardingPathSet
from sam.base.test.fixtures.srv6MorphicDict import srv6MorphicDictTemplate
from sam.base.switch import SWITCH_TYPE_DCNGATEWAY, SWITCH_TYPE_NPOP, Switch
from sam.switchController.test.component.fixtures.turbonetControllerStub import TurbonetControllerStub
from sam.base.command import CMD_STATE_SUCCESSFUL, CMD_TYPE_ADD_CLASSIFIER_ENTRY, CMD_TYPE_ADD_NSH_ROUTE
from sam.base.vnf import PREFERRED_DEVICE_TYPE_P4, PREFERRED_DEVICE_TYPE_SERVER, VNF_TYPE_RATELIMITER, VNFI
from sam.base.messageAgent import MEDIATOR_QUEUE, MSG_TYPE_P4CONTROLLER_CMD, P4CONTROLLER_QUEUE, TURBONET_ZONE


SFF1_DATAPATH_IP = "2.2.1.193"
SFF1_DATAPATH_MAC = "b8:ca:3a:65:f7:fa"  # ignore this
SFF1_CONTROLNIC_IP = "192.168.8.17"  # ignore this
SFF1_CONTROLNIC_MAC = "b8:ca:3a:65:f7:f8"   # ignore this
SFF1_SERVERID = 10001

SWITCH_SFF1_SWITCHID = 20
SWITCH_SFF1_LANIP = "2.2.2.128"  # prefix length is /27
SWITCH_SFF2_SWITCHID = 21
SWITCH_SFF2_LANIP = "2.2.3.0"  # prefix length is /27


class TestP4ControllerBase(IntTestBaseClass):
    MAXSFCIID = 0
    sfciCounter = 0

    def common_setup(self):
        logConfigur = LoggerConfigurator(__name__, './log',
                                         'testP4ControllerBase.log',
                                         level='debug')
        self.logger = logConfigur.getLogger()

        # setup
        self.sP = ShellProcessor()
        self.cleanLog()
        self.clearQueue()
        self.killAllModule()
        self.mediator = MediatorStub()
        self.measurer = MeasurementStub()
        self.turbonetControllerStub = TurbonetControllerStub()

        self.sfcList = []
        self.sfciList = []

        classifier = Switch(0, SWITCH_TYPE_DCNGATEWAY, DCN_GATEWAY_IP,
                            programmable=True)

        sfc1 = self.genLargeBandwidthSFC(classifier, zone=TURBONET_ZONE)
        rM = sfc1.routingMorphic
        sfci1 = self.genUniDirection10BackupP4ServerNFVISFCI(sfc1, routingMorphic=rM)

        sfc3 = self.genLowLatencySFC(classifier, zone=TURBONET_ZONE)
        rM = sfc3.routingMorphic
        sfci3 = self.genUniDirection10BackupP4ServerNFVISFCI(sfc3, routingMorphic=rM)

        sfc4 = self.genLargeConnectionSFC(classifier, zone=TURBONET_ZONE)
        rM = sfc4.routingMorphic
        sfci4 = self.genUniDirection10BackupP4ServerNFVISFCI(sfc4, routingMorphic=rM)

        sfc6 = self.genMixEquipmentSFC(classifier, zone=TURBONET_ZONE)
        rM = sfc6.routingMorphic
        sfci6 = self.genUniDirection10BackupP4ServerNFVISFCI(sfc6,
                                                             routingMorphic=rM)

        self.sfcList = [sfc1, sfc3, sfc4, sfc6]
        self.sfciList = [sfci1, sfci3, sfci4, sfci6]

    # def genUniDirection10BackupP4NFVISFCI(
    #         self, sfc, mappedVNFISeq=True, routingMorphic=None):
    #     if mappedVNFISeq:
    #         # vnfiSequence = self.gen10BackupP4VNFISequence(sfcLength)
    #         vnfiSequence = self.gen10BackupP4ServerVNFISequence(sfc)
    #     else:
    #         vnfiSequence = None
    #     fPS = self.genUniDirection10BackupP4ServerBasedForwardingPathSet(
    #                                                     sfc, vnfiSequence)
    #     return SFCI(self.assignSFCIID(), vnfiSequence, None,
    #                 # self.genUniDirection10BackupP4BasedForwardingPathSet(
    #                 #     sfcLength),
    #                 fPS,
    #                 routingMorphic)

    # def gen10BackupP4VNFISequence(self, sfcLength=1):
    #     # type: (int) -> List[List[VNFI]]
    #     # hard-code function
    #     vnfiSequence = []
    #     for index in range(sfcLength):
    #         vnfiSequence.append([])
    #         for iN in range(1):
    #             switch = Switch(SWITCH_SFF1_SWITCHID, SWITCH_TYPE_NPOP,
    #                             SWITCH_SFF1_LANIP, programmable=True)
    #             vnfi = VNFI(
    #                 VNF_TYPE_RATELIMITER, vnfType=VNF_TYPE_RATELIMITER,
    #                 vnfiID=uuid.uuid1(),
    #                 config=RateLimiterConfig(maxMbps=100),
    #                 node=switch)
    #             vnfiSequence[index].append(vnfi)
    #     return vnfiSequence

    # def genUniDirection10BackupP4BasedForwardingPathSet(self, sfciLength=1):
    #     # type: (int) -> ForwardingPathSet
    #     # please ref /sam/base/path.py
    #     # This function generate a sfc forwarding path for sfc "ingress->L2Forwarding->egress"
    #     # The primary forwarding path has two stage, the first stage is "ingress->L2Forwarding",
    #     # the second stage is "L2Forwarding->egress".
    #     # Each stage is a list of layeredNodeIDTuple which format is (stageIndex, nodeID)
    #     if sfciLength == 1:
    #         d0FP = [
    #             # (stageIndex, nodeID)
    #             [(0, 0), (0, 8), (0, 16), (0, SWITCH_SFF1_SWITCHID)],
    #             # Note that may be a serverID ocurred in path!
    #             [(1, SWITCH_SFF1_SWITCHID), (1, 16), (1, 8), (1, 0)]
    #         ]
    #     elif sfciLength == 2:
    #         d0FP = [
    #             [(0, 0), (0, 8), (0, 16), (0, SWITCH_SFF1_SWITCHID)],
    #             [(1, SWITCH_SFF1_SWITCHID), (1, SWITCH_SFF1_SWITCHID)],
    #             [(2, SWITCH_SFF1_SWITCHID), (2, 16), (2, 8), (2, 0)]
    #         ]
    #     elif sfciLength == 3:
    #         d0FP = [
    #             [(0, 0), (0, 8), (0, 16), (0, SWITCH_SFF1_SWITCHID)],
    #             [(1, SWITCH_SFF1_SWITCHID), (1, SWITCH_SFF1_SWITCHID)],
    #             [(2, SWITCH_SFF1_SWITCHID), (2, SWITCH_SFF1_SWITCHID)],
    #             [(3, SWITCH_SFF1_SWITCHID), (3, 16), (3, 8), (3, 0)]
    #         ]
    #     else:
    #         raise ValueError("Unimplement sfci length!")
    #     primaryForwardingPath = {DIRECTION0_PATHID_OFFSET: d0FP}
    #     mappingType = MAPPING_TYPE_MMLPSFC  # This is your mapping algorithm type
    #     backupForwardingPath = {}   # you don't need to care about backupForwardingPath
    #     return ForwardingPathSet(primaryForwardingPath, mappingType,
    #                              backupForwardingPath)

    def genUniDirection10BackupP4ServerNFVISFCI(
            self, sfc, mappedVNFISeq=True, routingMorphic=None):
        # type: (SFC, bool, RoutingMorphic) -> SFCI
        if mappedVNFISeq:
            vnfiSequence = self.gen10BackupP4ServerVNFISequence(sfc)
        else:
            vnfiSequence = None
        fPS = self.genUniDirection10BackupP4ServerBasedForwardingPathSet(
            sfc, vnfiSequence)
        return SFCI(self.assignSFCIID(), vnfiSequence, None,
                    fPS, routingMorphic)

    def gen10BackupP4ServerVNFISequence(self, sfc):
        # type: (SFC) -> List[List[VNFI]]
        # hard-code function
        vnfiSequence = []
        for idx, vnf in enumerate(sfc.vnfSequence):
            vnfiSequence.append([])
            vnfType = vnf.vnfType
            config = vnf.config
            for iN in range(1):
                if vnf.preferredDeviceType == PREFERRED_DEVICE_TYPE_P4:
                    node = Switch(SWITCH_SFF1_SWITCHID, SWITCH_TYPE_NPOP,
                                  SWITCH_SFF1_LANIP, programmable=True)
                elif vnf.preferredDeviceType == PREFERRED_DEVICE_TYPE_SERVER:
                    node = Server("ens3", SFF1_DATAPATH_IP, SERVER_TYPE_NFVI)
                    node.setServerID(SFF1_SERVERID)
                    node.setControlNICIP(SFF1_CONTROLNIC_IP)
                    node.setControlNICMAC(SFF1_CONTROLNIC_MAC)
                    node.setDataPathNICMAC(SFF1_DATAPATH_MAC)
                else:
                    raise ValueError(
                        "Unknown prefered device type {0}".format(
                            vnf.preferredDeviceType))

                vnfi = VNFI(vnfType, vnfType=vnfType,
                            vnfiID=uuid.uuid1(), config=config, node=node)
                vnfiSequence[idx].append(vnfi)
        return vnfiSequence

    def genUniDirection10BackupP4ServerBasedForwardingPathSet(
            self, sfc, vnfiSequence):
        # type: (SFC, List[VNFI]) -> ForwardingPathSet
        # please ref /sam/base/path.py
        # This function generate a sfc forwarding path for sfc "ingress->L2Forwarding->egress"
        # The primary forwarding path has two stage, the first stage is "ingress->L2Forwarding",
        # the second stage is "L2Forwarding->egress".
        # Each stage is a list of layeredNodeIDTuple which format is (stageIndex, nodeID)
        d0FP = []
        for idx, vnf in enumerate(sfc.vnfSequence):
            if idx == 0:
                srcNodeID = 0
                dstNode = vnfiSequence[idx][0].node
                dstNodeID = self.getNodeID(dstNode)
            elif idx == len(sfc.vnfSequence)-1:
                srcNode = vnfiSequence[idx-1][0].node
                srcNodeID = self.getNodeID(srcNode)
                dstNodeID = 0
            else:
                srcNode = vnfiSequence[idx-1][0].node
                srcNodeID = self.getNodeID(srcNode)
                dstNode = vnfiSequence[idx][0].node
                dstNodeID = self.getNodeID(dstNode)
            segPath = self.getSegPath(srcNodeID, dstNodeID, idx)
            d0FP.append(segPath)

        pSF = PathServerFiller()
        d1FP = pSF.reverseForwardingPath(d0FP)
        primaryForwardingPath = {DIRECTION0_PATHID_OFFSET: d0FP}
        if len(sfc.directions) == 2:
            primaryForwardingPath[DIRECTION1_PATHID_OFFSET] = d1FP
        mappingType = MAPPING_TYPE_MMLPSFC  # This is your mapping algorithm type
        backupForwardingPath = {}   # you don't need to care about backupForwardingPath
        return ForwardingPathSet(primaryForwardingPath, mappingType,
                                 backupForwardingPath)

    def getNodeID(self, node):
        # type: (Union[Server, Switch]) -> int
        if type(node) == Server:
            nodeID = node.getServerID()
        elif type(node) == Switch:
            nodeID = node.switchID
        else:
            raise ValueError("Unknown node type {0}".format(type(node)))
        return nodeID

    def getSegPath(self, srcNodeID, dstNodeID, stageNum):
        # type: (int, int, int) -> List[Tuple[int, int]]
        if srcNodeID == 0 and dstNodeID == SWITCH_SFF1_SWITCHID:
            segPath = [(stageNum, 0), (stageNum, 8), (stageNum, 16),
                       (stageNum, SWITCH_SFF1_SWITCHID)]
        elif dstNodeID == 0 and srcNodeID == SWITCH_SFF1_SWITCHID:
            segPath = [(stageNum, SWITCH_SFF1_SWITCHID),
                       (stageNum, 16), (stageNum, 8), (stageNum, 0)]
        elif srcNodeID == 0 and dstNodeID == SFF1_SERVERID:
            segPath = [(stageNum, 0), (stageNum, 6),
                       (stageNum, 14), (stageNum, SFF1_SERVERID)]
        elif dstNodeID == 0 and srcNodeID == SFF1_SERVERID:
            segPath = [(stageNum, SFF1_SERVERID), (stageNum, 14),
                       (stageNum, 6), (stageNum, 0)]
        elif srcNodeID == SWITCH_SFF1_SWITCHID and dstNodeID == SWITCH_SFF1_SWITCHID:
            segPath = [(stageNum, SWITCH_SFF1_SWITCHID),
                       (stageNum, SWITCH_SFF1_SWITCHID)]
        elif srcNodeID == SFF1_SERVERID and dstNodeID == SFF1_SERVERID:
            segPath = [(stageNum, SFF1_SERVERID), (stageNum, SFF1_SERVERID)]
        elif srcNodeID == SFF1_SERVERID and dstNodeID == SFF1_SERVERID:
            segPath = [(stageNum, SFF1_SERVERID), (stageNum, SFF1_SERVERID)]
        elif srcNodeID == SWITCH_SFF1_SWITCHID and dstNodeID == SFF1_SERVERID:
            segPath = [
                (stageNum, SWITCH_SFF1_SWITCHID),
                (stageNum, 16),
                (stageNum, 8),
                (stageNum, 0),
                (stageNum, 6),
                (stageNum, 14),
                (stageNum, SFF1_SERVERID)]
        elif srcNodeID == SWITCH_SFF1_SWITCHID and dstNodeID == SFF1_SERVERID:
            segPath = [
                (stageNum, SFF1_SERVERID),
                (stageNum, 14),
                (stageNum, 6),
                (stageNum, 0),
                (stageNum, 8),
                (stageNum, 16),
                (stageNum, SWITCH_SFF1_SWITCHID)]
        else:
            raise ValueError("Unknown implementation.")
        return segPath

    def exerciseAddSFCAndSFCI(self):
        for idx in [0, 1, 2]:
            self.logger.info("test idx {0}".format(idx))
            # exercise
            self.addSFCCmd = self.mediator.genCMDAddSFC(self.sfcList[idx])
            self.sendCmd(P4CONTROLLER_QUEUE, MSG_TYPE_P4CONTROLLER_CMD,
                         self.addSFCCmd)
            self.verifyAddSFCCmdRply()

            # exercise
            self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfcList[idx],
                                                          self.sfciList[idx])
            self.sendCmd(P4CONTROLLER_QUEUE, MSG_TYPE_P4CONTROLLER_CMD,
                         self.addSFCICmd)

            # verify
            # self.verifyTurbonetRecvAddClassifierEntryCmd(self.sfcList[idx])
            # self.verifyTurbonetRecvAddRouteEntryCmd(self.sfciList[idx])
            self.verifyTurbonetRecvAddSFCICmd(self.sfcList[idx], self.sfciList[idx])
            self.verifyAddSFCICmdRply()

    def verifyAddSFCCmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCCmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        assert cmdRply.attributes['zone'] == TURBONET_ZONE

    def verifyTurbonetRecvAddSFCICmd(self, sfc, sfci):
        # type: (SFC, SFCI) -> None
        cmdNum = len(sfc.directions)

        pFPDict = sfci.forwardingPathSet.primaryForwardingPath
        maxCmdCnt = 0
        for pathIdx in [DIRECTION0_PATHID_OFFSET, DIRECTION1_PATHID_OFFSET]:
            if pathIdx in pFPDict:
                pFP = pFPDict[pathIdx]
                for segPath in pFP:
                    if len(segPath) == 2:
                        continue
                    for idx, (stageNum, nodeID) in enumerate(segPath):
                        if (self.isSwitchID(nodeID) 
                                and idx != 0 
                                and idx != len(segPath)-1):
                            maxCmdCnt += 1

        self.turbonetControllerStub.recvCmd(
            [CMD_TYPE_ADD_CLASSIFIER_ENTRY, CMD_TYPE_ADD_NSH_ROUTE], 
            [cmdNum, maxCmdCnt])

    def verifyTurbonetRecvAddClassifierEntryCmd(self, sfc):
        # type: (SFC) -> None
        cmdNum = len(sfc.directions)
        self.turbonetControllerStub.recvCmd(
            [CMD_TYPE_ADD_CLASSIFIER_ENTRY], cmdNum)

    def verifyTurbonetRecvAddRouteEntryCmd(self, sfci):
        # type: (SFCI) -> None
        pFPDict = sfci.forwardingPathSet.primaryForwardingPath
        maxCmdCnt = 0
        for pathIdx in [DIRECTION0_PATHID_OFFSET, DIRECTION1_PATHID_OFFSET]:
            if pathIdx in pFPDict:
                pFP = pFPDict[pathIdx]
                for segPath in pFP:
                    if len(segPath) == 2:
                        continue
                    for idx, (stageNum, nodeID) in enumerate(segPath):
                        if (self.isSwitchID(nodeID) 
                                and idx != 0 
                                and idx != len(segPath)-1):
                            maxCmdCnt += 1
        self.turbonetControllerStub.recvCmd(
            [CMD_TYPE_ADD_NSH_ROUTE], maxCmdCnt)

    def isSwitchID(self, nodeID):
        # type: (int) -> bool
        return nodeID <= 10000

    def isServerID(self, nodeID):
        # type: (int) -> bool
        return nodeID > 10000

    def verifyAddSFCICmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        assert cmdRply.attributes['zone'] == TURBONET_ZONE

    def verifyDelSFCICmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        assert cmdRply.attributes['zone'] == TURBONET_ZONE

    def verifyDelSFCCmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCCmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        assert cmdRply.attributes['zone'] == TURBONET_ZONE
