#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is an example for writing integrate test
The work flow:
    * generate 5 addSFC and 5 addSFCI command to dispatcher
    * generate 1 server failure using simulator, check whether regulator enable failover of the corresponding SFCI
        * [error] server 14481 down
        * [error] switch 421 down
        * [error] link 928 421 down

Usage of this unit test:
    python -m pytest ./test_3.py -s --disable-warnings
'''

import uuid
from typing import Tuple

import pytest

from sam.base.command import CMD_TYPE_HANDLE_FAILURE_ABNORMAL, Command
from sam.base.compatibility import screenInput
from sam.base.messageAgent import DISPATCHER_QUEUE, MSG_TYPE_REGULATOR_CMD, \
                                    REGULATOR_QUEUE, TURBONET_ZONE
from sam.base.path import DIRECTION0_PATHID_OFFSET, DIRECTION1_PATHID_OFFSET
from sam.base.request import REQUEST_TYPE_ADD_SFC, REQUEST_TYPE_ADD_SFCI, \
                        REQUEST_TYPE_DEL_SFC, REQUEST_TYPE_DEL_SFCI, \
                        REQUEST_TYPE_UPDATE_SFC_STATE, Request
from sam.base.sfc import SFCI
from sam.base.sfcConstant import MANUAL_SCALE, STATE_MANUAL
from sam.test.integrate.intTestBase import IntTestBaseClass
from sam.base.messageAgentAuxillary.msgAgentRPCConf import ABNORMAL_DETECTOR_IP, \
                                ABNORMAL_DETECTOR_PORT, REGULATOR_IP, REGULATOR_PORT

class TestAddSFCClass(IntTestBaseClass):
    @pytest.fixture(scope="function")
    def setup_oneSFC(self):
        self.common_setup()

        self.sfcList = []
        self.sfciList = []

        # you can overwrite following function to test different sfc/sfci
        classifier = None
        sfc1 = self.genLargeBandwidthSFC(classifier, TURBONET_ZONE)
        rM = sfc1.routingMorphic
        sfci1 = self.genSFCITemplate(rM)

        sfc2 = self.genHighAvaSFC(classifier, TURBONET_ZONE)
        rM = sfc2.routingMorphic
        sfci2 = self.genSFCITemplate(rM)

        sfc3 = self.genLowLatencySFC(classifier, TURBONET_ZONE)
        rM = sfc3.routingMorphic
        sfci3 = self.genSFCITemplate(rM)

        sfc4 = self.genLargeConnectionSFC(classifier, TURBONET_ZONE)
        rM = sfc4.routingMorphic
        sfci4 = self.genSFCITemplate(rM)

        sfc5 = self.genBestEffortSFC(classifier, TURBONET_ZONE)
        rM = sfc5.routingMorphic
        sfci5 = self.genSFCITemplate(rM)

        self.sfcList = [sfc1, sfc2, sfc3, sfc4, sfc5]
        self.sfciList = [sfci1, sfci2, sfci3, sfci4, sfci5]

        yield

        # teardown
        self.clearQueue()
        self.killAllModule()

    def test_fiveSFCs(self, setup_oneSFC):
        # exercise
        for idx, sfc in enumerate(self.sfcList):
            rq = Request(uuid.uuid1(), uuid.uuid1(), REQUEST_TYPE_ADD_SFC,
                attributes={
                    "sfc": sfc,
                    "zone": TURBONET_ZONE
                })
            self.sendRequest(DISPATCHER_QUEUE, rq)

        self.logger.info("Please check orchestrator if recv a command reply?"\
                        "Then press andy key to continue!")
        screenInput()

        # exercise
        for idx, sfci in enumerate(self.sfciList):
            sfc = self.getSFCFromDB(self.sfcList[idx].sfcUUID)
            if sfc.scalingMode == MANUAL_SCALE:
                rq = Request(uuid.uuid1(), uuid.uuid1(), REQUEST_TYPE_ADD_SFCI,
                    attributes={
                        "sfc": sfc,
                        "sfci": sfci,
                        "zone": TURBONET_ZONE
                    })
                self.logger.info("sfc is {0}".format(sfc))
                self.sendRequest(DISPATCHER_QUEUE, rq)
            else:
                while True:
                    sfciIDList = self.getSFCIIDListFromDB(self.sfcList[idx].sfcUUID)
                    if len(sfciIDList) >= 1:
                        for sfciID in sfciIDList:
                            sfci = self.getSFCIFromDB(sfciID)
                            self.sfciList[idx] = sfci
                        break

        self.logger.info("Please check orchestrator if recv a command reply?"\
                        "Then press andy key to continue!")
        screenInput()

        # exercise
        while True:
            abnormalType = screenInput("Please input abnormal type: switch, server, link.\n")
            if abnormalType == "switch":
                switchIDList = []
                for sfci in self.sfciList:
                    updatedSFCI = self.getSFCIFromDB(sfci.sfciID)
                    switchIDList.extend(self.getAllSwitchIDFromSFCI(updatedSFCI))
                self.logger.info("Please input abnormal switchID from "
                                    "candidate switch list {0}".format(switchIDList))
                abnSwitchID = int(screenInput())
                self.logger.info("Please input abnormal serverID to "
                                    " simulator: switch {0} down ".format(abnSwitchID))
                cmd = self.genAbnormalSwitchHandleCommand(abnSwitchID)
                break
            elif abnormalType == "server":
                serverIDList = []
                for sfci in self.sfciList:
                    updatedSFCI = self.getSFCIFromDB(sfci.sfciID)
                    serverIDList.extend(self.getAllServerIDFromSFCI(updatedSFCI))
                self.logger.info("Please input abnormal serverID from "
                                    "candidate server list {0}".format(serverIDList))
                abnServerID = int(screenInput())
                self.logger.info("Please input abnormal serverID to "
                                    " simulator: server {0} down ".format(abnServerID))
                cmd = self.genAbnormalServerHandleCommand(abnServerID)
                break
            elif abnormalType == "link":
                linkIDList = []
                for sfci in self.sfciList:
                    updatedSFCI = self.getSFCIFromDB(sfci.sfciID)
                    linkIDList.extend(self.getAllLinkIDFromSFCI(updatedSFCI))
                self.logger.info("Please input abnormal linkID from "
                                    "candidate link list {0}".format(linkIDList))
                srcNodeID = int(screenInput("srcNodeID:"))
                dstNodeID = int(screenInput("dstNodeID:"))
                abnLinkID = (srcNodeID, dstNodeID)
                self.logger.info("Please input abnormal linkID to "
                                    " simulator: link {0} {1} down ".format(
                                                    abnLinkID[0], abnLinkID[1]))
                screenInput()
                cmd = self.genAbnormalLinkHandleCommand(abnLinkID)
                break
            else:
                self.logger.info("Unknown abnormal type")
        # self.sendCmd(REGULATOR_QUEUE, MSG_TYPE_REGULATOR_CMD, cmd)
        self.setMessageAgentListenSocket(ABNORMAL_DETECTOR_IP, 
                                            ABNORMAL_DETECTOR_PORT)
        self.sendCmdByRPC(REGULATOR_IP, REGULATOR_PORT, MSG_TYPE_REGULATOR_CMD, cmd)
        self.logger.info("Please check regulator if affected SFCI recovered?"\
                        "Then press andy key to continue!")
        screenInput()

        # setup
        for idx, sfc in enumerate(self.sfcList):
            rq = Request(uuid.uuid1(), uuid.uuid1(), REQUEST_TYPE_UPDATE_SFC_STATE,
                attributes={
                    "sfc": self.getSFCFromDB(self.sfcList[idx].sfcUUID),
                    "newState": STATE_MANUAL,
                    "zone": TURBONET_ZONE
                })
            self.sendRequest(REGULATOR_QUEUE, rq)

        self.logger.info("Please check if regulator recvs requests? "\
                        "And SFC state turn to STATE_MANUAL? " \
                        "Then press andy key to continue!")
        screenInput()

        # exercise
        for idx, sfci in enumerate(self.sfciList):
            rq = Request(uuid.uuid1(), uuid.uuid1(), REQUEST_TYPE_DEL_SFCI,
                attributes={
                    "sfc": self.getSFCFromDB(self.sfcList[idx].sfcUUID),
                    "sfci": sfci,
                    "zone": TURBONET_ZONE
                })
            self.sendRequest(REGULATOR_QUEUE, rq)

        self.logger.info("Please check orchestrator if recv a command reply?"\
                        "Then press andy key to continue!")
        screenInput()

        # exercise
        for idx, sfc in enumerate(self.sfcList):
            rq = Request(uuid.uuid1(), uuid.uuid1(), REQUEST_TYPE_DEL_SFC,
                attributes={
                    "sfc": self.getSFCFromDB(self.sfcList[idx].sfcUUID),
                    "zone": TURBONET_ZONE
                })
            self.sendRequest(REGULATOR_QUEUE, rq)

        self.logger.info("Please check orchestrator if recv a command reply?"\
                        "Then press andy key to continue!")
        screenInput()

    def getAllSwitchIDFromSFCI(self, sfci):
        # type: (SFCI) -> list(int)
        switchDict = {}
        pFP = sfci.forwardingPathSet.primaryForwardingPath
        for pathIDOffset in [DIRECTION0_PATHID_OFFSET, DIRECTION1_PATHID_OFFSET]:
            if pathIDOffset in pFP.keys():
                uniPFP = pFP[pathIDOffset]
                for segPath in uniPFP:
                    for segNodeID in segPath:
                        nodeID = segNodeID[1]
                        self.logger.info("nodeID is {0}".format(nodeID))
                        if self.isSwitchID(nodeID):
                            switchDict[nodeID] = 1
        return list(switchDict.keys())

    def getAllServerIDFromSFCI(self, sfci):
        # type: (SFCI) -> list(int)
        serverDict = {}
        pFP = sfci.forwardingPathSet.primaryForwardingPath
        for pathIDOffset in [DIRECTION0_PATHID_OFFSET, DIRECTION1_PATHID_OFFSET]:
            if pathIDOffset in pFP.keys():
                uniPFP = pFP[pathIDOffset]
                for segPath in uniPFP:
                    for segNodeID in segPath:
                        nodeID = segNodeID[1]
                        self.logger.info("nodeID is {0}".format(nodeID))
                        if self.isServerID(nodeID):
                            serverDict[nodeID] = 1
        return list(serverDict.keys())

    def getAllLinkIDFromSFCI(self, sfci):
        # type: (SFCI) -> list(Tuple[int, int])
        linkDict = {}
        pFP = sfci.forwardingPathSet.primaryForwardingPath
        for pathIDOffset in [DIRECTION0_PATHID_OFFSET, DIRECTION1_PATHID_OFFSET]:
            if pathIDOffset in pFP.keys():
                uniPFP = pFP[pathIDOffset]
                for segPath in uniPFP:
                    for idx in range(len(segPath)-1):
                        segNodeID = segPath[idx]
                        nextSegNodeID = segPath[idx+1]
                        srcNodeID = segNodeID[1]
                        dstNodeID = nextSegNodeID[1]
                        linkID = (srcNodeID, dstNodeID)
                        self.logger.info("linkID is {0}".format(linkID))
                        linkDict[linkID] = 1
        return list(linkDict.keys())

    def isServerID(self, nodeID):
        return nodeID > 10000
    
    def isSwitchID(self, nodeID):
        return nodeID <= 10000

    def genAbnormalServerHandleCommand(self, serverID):
        detectionDict = {
            "failure":{
                "switchIDList":[],
                "serverIDList":[],
                "linkIDList":[]
            },
            "abnormal":{
                "switchIDList":[],
                "serverIDList":[serverID],
                "linkIDList":[]
            }
        }
        allZoneDetectionDict={TURBONET_ZONE: detectionDict}
        attr = {
            "allZoneDetectionDict": allZoneDetectionDict
        }
        cmd = Command(CMD_TYPE_HANDLE_FAILURE_ABNORMAL, uuid.uuid1(), attributes=attr)
        return cmd

    def genAbnormalSwitchHandleCommand(self, switchID):
        detectionDict = {
            "failure":{
                "switchIDList":[],
                "serverIDList":[],
                "linkIDList":[]
            },
            "abnormal":{
                "switchIDList":[switchID],
                "serverIDList":[],
                "linkIDList":[]
            }
        }
        allZoneDetectionDict={TURBONET_ZONE: detectionDict}
        attr = {
            "allZoneDetectionDict": allZoneDetectionDict
        }
        cmd = Command(CMD_TYPE_HANDLE_FAILURE_ABNORMAL, uuid.uuid1(), attributes=attr)
        return cmd

    def genAbnormalLinkHandleCommand(self, linkID):
        detectionDict = {
            "failure":{
                "switchIDList":[],
                "serverIDList":[],
                "linkIDList":[]
            },
            "abnormal":{
                "switchIDList":[],
                "serverIDList":[],
                "linkIDList":[linkID]
            }
        }
        allZoneDetectionDict={TURBONET_ZONE: detectionDict}
        attr = {
            "allZoneDetectionDict": allZoneDetectionDict
        }
        cmd = Command(CMD_TYPE_HANDLE_FAILURE_ABNORMAL, uuid.uuid1(), attributes=attr)
        return cmd
