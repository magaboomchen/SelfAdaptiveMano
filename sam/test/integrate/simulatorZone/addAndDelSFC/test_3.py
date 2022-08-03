#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is an example for writing integrate test
The work flow:
    * generate 5 addSFC and 5 addSFCI command to dispatcher
    * generate 1 server failure using simulator, check whether regulator enable failover of the corresponding SFCI

Usage of this unit test:
    python -m pytest ./test_3.py -s --disable-warnings
'''

import uuid

import pytest
from sam.base.command import CMD_TYPE_HANDLE_FAILURE_ABNORMAL, Command

from sam.base.compatibility import screenInput
from sam.base.messageAgent import DISPATCHER_QUEUE, MSG_TYPE_REGULATOR_CMD, REGULATOR_QUEUE, SIMULATOR_ZONE, TURBONET_ZONE
from sam.base.path import DIRECTION0_PATHID_OFFSET, DIRECTION1_PATHID_OFFSET
from sam.base.request import REQUEST_TYPE_ADD_SFC, REQUEST_TYPE_ADD_SFCI, \
                        REQUEST_TYPE_DEL_SFC, REQUEST_TYPE_DEL_SFCI, Request
from sam.base.sfc import SFCI
from sam.test.integrate.intTestBase import IntTestBaseClass

MANUAL_TEST = True


class TestAddSFCClass(IntTestBaseClass):
    @pytest.fixture(scope="function")
    def setup_oneSFC(self):
        self.common_setup()

        self.sfcList = []
        self.sfciList = []

        # you can overwrite following function to test different sfc/sfci
        classifier = None
        sfc1 = self.genLargeBandwidthSFC(classifier)
        sfci1 = self.genSFCITemplate()

        sfc2 = self.genHighAvaSFC(classifier)
        sfci2 = self.genSFCITemplate()

        sfc3 = self.genLowLatencySFC(classifier)
        sfci3 = self.genSFCITemplate()

        sfc4 = self.genLargeConnectionSFC(classifier)
        sfci4 = self.genSFCITemplate()

        sfc5 = self.genBestEffortSFC(classifier)
        sfci5 = self.genSFCITemplate()

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
                    "zone": SIMULATOR_ZONE
                })
            self.sendRequest(DISPATCHER_QUEUE, rq)

        self.logger.info("Please check orchestrator if recv a command reply?"\
                        "Then press andy key to continue!")
        screenInput()

        # exercise
        for idx, sfci in enumerate(self.sfciList):
            sfc = self.getSFCFromDB(self.sfcList[idx].sfcUUID)
            rq = Request(uuid.uuid1(), uuid.uuid1(), REQUEST_TYPE_ADD_SFCI,
                attributes={
                    "sfc": sfc,
                    "sfci": sfci,
                    "zone": SIMULATOR_ZONE
                })
            self.logger.info("sfc is {0}".format(sfc))
            self.sendRequest(DISPATCHER_QUEUE, rq)

        self.logger.info("Please check orchestrator if recv a command reply?"\
                        "Then press andy key to continue!")
        screenInput()

        # exercise
        serverIDList = []
        for sfci in self.sfciList:
            updatedSFCI = self.getSFCIFromDB(sfci.sfciID)
            serverIDList.extend(self.getAllServerIDFromSFCI(updatedSFCI))
        self.logger.info("Please input abnormal serverID from "
                            "candidate server list {0}".format(serverIDList))
        abnServerID = int(screenInput())
        cmd = self.genAbnormalServerHandleCommand(abnServerID)
        self.sendCmd(REGULATOR_QUEUE, MSG_TYPE_REGULATOR_CMD, cmd)

        self.logger.info("Please check regulator if affected SFCI recovered?"\
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
            self.sendRequest(DISPATCHER_QUEUE, rq)

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
            self.sendRequest(DISPATCHER_QUEUE, rq)

        self.logger.info("Please check orchestrator if recv a command reply?"\
                        "Then press andy key to continue!")
        screenInput()

    def getAllSwitchIDFromSFCI(self, sfci):
        # type: (SFCI) -> list(int)
        switchDict = {}
        pFP = sfci.forwardingPathSet.primaryForwardingPath
        for pathIDOffset in [DIRECTION0_PATHID_OFFSET, DIRECTION1_PATHID_OFFSET]:
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
