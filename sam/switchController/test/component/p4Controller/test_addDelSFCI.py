#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is the test for p4 controller
The work flow:
    * Mediator sends 'ADD_SFCI command' to p4 controller;
    * P4 controller processes the command and then send back a command reply to the mediator;
    PS1:The 'ADD_SFCI command' and the corresponding 'ADD_SFCI command reply' have same cmdID;
    PS2: Class TestBase and IntTestBaseClass has many useful function;

Usage of this unit test:
    python -m pytest ./test_addDelSFCI.py -s --disable-warnings
'''

import pytest

from sam.base.sfc import SFC, SFCI
from sam.base.compatibility import screenInput
from sam.base.command import CMD_TYPE_DEL_CLASSIFIER_ENTRY, CMD_TYPE_DEL_NSH_ROUTE
from sam.base.messageAgent import MSG_TYPE_P4CONTROLLER_CMD, P4CONTROLLER_QUEUE
from sam.base.path import DIRECTION0_PATHID_OFFSET, DIRECTION1_PATHID_OFFSET
from sam.switchController.test.component.p4ControllerTestBase import TestP4ControllerBase

ENABLE_JOINT_TEST = True


class TestAddSFCIClass(TestP4ControllerBase):
    @pytest.fixture(scope="function")
    def setup_addSFCIWithP4VNFIOnASwitch(self):
        self.common_setup()

        self.logger.info("Please start P4Controller," \
                    "Then press any key to continue!")
        screenInput()

        yield
        # teardown
        self.clearQueue()
        self.killAllModule()

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_addSFCIWithP4VNFIOnASwitch(self, 
                                        setup_addSFCIWithP4VNFIOnASwitch):
        self.logger.info("Deploying SFCI to P4 controller.")
        self.exerciseAddSFCAndSFCI(jointTestMode=ENABLE_JOINT_TEST)
        self.logger.info("Deploying SFCI to P4 controller finish.")

        self.logger.info("Please check results," \
                    "Then press any key to continue!")
        screenInput()

        assert 1 == 1

    @pytest.fixture(scope="function")
    def setup_delSFCIWithVNFIOnAServer(self):
        self.common_setup()

        self.logger.info("Please start P4Controller," \
                    "Then press any key to continue!")
        screenInput()

        self.logger.info("Deploying SFCI to P4 controller.")
        self.exerciseAddSFCAndSFCI(jointTestMode=ENABLE_JOINT_TEST)
        self.logger.info("Deploying SFCI to P4 controller finish.")

        yield
        # teardown
        self.clearQueue()
        self.killAllModule()

    @pytest.mark.skip(reason='Skip temporarily')
    def test_delSFCIWithVNFIOnAServer(self,
                                            setup_delSFCIWithVNFIOnAServer):
        # exercise
        self.logger.info("Deleting SFCI to P4 controller.")
        self.exerciseDelSFCAndSFCI(jointTestMode=ENABLE_JOINT_TEST)
        self.logger.info("Deleting SFCI to P4 controller finish.")

        self.logger.info("Please check results," \
                    "Then press any key to continue!")
        screenInput()

        yield
        # teardown
        self.clearQueue()
        self.killAllModule()

    def exerciseDelSFCAndSFCI(self, jointTestMode=False):
        for idx in [0,1,2]:
            self.logger.info("test idx {0}".format(idx))
            # exercise
            self.delSFCICmd = self.mediator.genCMDDelSFCI(self.sfcList[idx],
                                                        self.sfciList[idx])
            self.sendCmd(P4CONTROLLER_QUEUE, MSG_TYPE_P4CONTROLLER_CMD,
                                                self.delSFCICmd)

            # verify
            if not jointTestMode:
                self.verifyTurbonetRecvDelSFCICmd(self.sfciList[idx], self.sfcList[idx])
                self.verifyDelSFCICmdRply()

            # exercise
            self.delSFCCmd = self.mediator.genCMDDelSFC(self.sfcList[idx],
                                                        self.sfciList[idx])
            self.sendCmd(P4CONTROLLER_QUEUE, MSG_TYPE_P4CONTROLLER_CMD,
                                                self.delSFCCmd)

            if not jointTestMode:
                self.verifyDelSFCCmdRply()

    def verifyTurbonetRecvDelSFCICmd(self, sfc, sfci):
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
                                and idx !=0 
                                and idx !=len(segPath)-1):
                            maxCmdCnt += 1

        self.turbonetControllerStub.recvCmd(
            [CMD_TYPE_DEL_CLASSIFIER_ENTRY, CMD_TYPE_DEL_NSH_ROUTE], 
            [cmdNum, maxCmdCnt])

    def verifyTurbonetRecvDelClassifierEntryCmd(self, sfc):
        # type: (SFC) -> None
        cmdNum = len(sfc.directions)
        self.turbonetControllerStub.recvCmd([CMD_TYPE_DEL_CLASSIFIER_ENTRY], cmdNum)

    def verifyTurbonetRecvDelRouteEntryCmd(self, sfci):
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
                                and idx !=0 
                                and idx !=len(segPath)-1):
                            maxCmdCnt += 1
                self.turbonetControllerStub.recvCmd([CMD_TYPE_DEL_NSH_ROUTE], maxCmdCnt)
