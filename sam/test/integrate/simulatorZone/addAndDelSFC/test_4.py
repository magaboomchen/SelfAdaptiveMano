#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is an example for writing integrate test
The work flow:
    * generate 5 addSFC and 5 addSFCI command to dispatcher
    * generate 1 traffic to sfci
        * add traffic 10001 10001 0 --trafficRate 10000

Usage of this unit test:
    python -m pytest ./test_4.py -s --disable-warnings
'''

import uuid
from typing import Tuple

import pytest

from sam.base.command import CMD_TYPE_HANDLE_FAILURE_ABNORMAL, Command
from sam.base.compatibility import screenInput
from sam.base.messageAgent import REGULATOR_QUEUE, SIMULATOR_ZONE
from sam.base.path import DIRECTION0_PATHID_OFFSET, DIRECTION1_PATHID_OFFSET
from sam.base.request import REQUEST_TYPE_ADD_SFC, REQUEST_TYPE_ADD_SFCI, \
                        REQUEST_TYPE_DEL_SFC, REQUEST_TYPE_DEL_SFCI, \
                        REQUEST_TYPE_UPDATE_SFC_STATE, Request
from sam.base.sfc import SFCI
from sam.base.sfcConstant import MANUAL_SCALE, STATE_MANUAL
from sam.test.integrate.intTestBase import IntTestBaseClass


class TestAddSFCClass(IntTestBaseClass):
    @pytest.fixture(scope="function")
    def setup_oneSFC(self):
        self.common_setup()

        self.sfcList = []
        self.sfciList = []

        # you can overwrite following function to test different sfc/sfci
        classifier = None
        sfc1 = self.genLargeBandwidthSFC(classifier)
        rM = sfc1.routingMorphic
        sfci1 = self.genSFCITemplate(rM)

        sfc2 = self.genHighAvaSFC(classifier)
        rM = sfc2.routingMorphic
        sfci2 = self.genSFCITemplate(rM)

        sfc3 = self.genLowLatencySFC(classifier)
        rM = sfc3.routingMorphic
        sfci3 = self.genSFCITemplate(rM)

        sfc4 = self.genLargeConnectionSFC(classifier)
        rM = sfc4.routingMorphic
        sfci4 = self.genSFCITemplate(rM)

        sfc5 = self.genBestEffortSFC(classifier)
        rM = sfc5.routingMorphic
        sfci5 = self.genSFCITemplate(rM)

        # self.sfcList = [sfc1, sfc2, sfc3, sfc4, sfc5]
        # self.sfciList = [sfci1, sfci2, sfci3, sfci4, sfci5]

        # self.sfcList = [sfc2, sfc3, sfc4, sfc5]
        # self.sfciList = [sfci2, sfci3, sfci4, sfci5]

        self.sfcList = [sfc5]
        self.sfciList = [sfci5]

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
                    "zone": SIMULATOR_ZONE
                })
            self.sendRequest(REGULATOR_QUEUE, rq)

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
                        "zone": SIMULATOR_ZONE
                    })
                self.logger.info("sfc is {0}".format(sfc))
                self.sendRequest(REGULATOR_QUEUE, rq)
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
        screenInput("Please input large traffic to sfci.\n")
        self.logger.info("Please check regulator if affected SFCI scaling up?"\
                        "Then press andy key to continue!")
        screenInput()

        # setup
        for idx, sfc in enumerate(self.sfcList):
            rq = Request(uuid.uuid1(), uuid.uuid1(), REQUEST_TYPE_UPDATE_SFC_STATE,
                attributes={
                    "sfc": self.getSFCFromDB(self.sfcList[idx].sfcUUID),
                    "newState": STATE_MANUAL,
                    "zone": SIMULATOR_ZONE
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
                    "zone": SIMULATOR_ZONE
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
                    "zone": SIMULATOR_ZONE
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
        allZoneDetectionDict={SIMULATOR_ZONE: detectionDict}
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
        allZoneDetectionDict={SIMULATOR_ZONE: detectionDict}
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
        allZoneDetectionDict={SIMULATOR_ZONE: detectionDict}
        attr = {
            "allZoneDetectionDict": allZoneDetectionDict
        }
        cmd = Command(CMD_TYPE_HANDLE_FAILURE_ABNORMAL, uuid.uuid1(), attributes=attr)
        return cmd
