#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is an example for writing unit test for simulator (test _addSFCIHandler)
The work flow:
    * Mediator sends ‘ADD_SFCI command’ to simulator;
    * Simulator processes the command and then send back a command reply to the mediator;
    PS1:The ‘ADD_SFCI command’ and the corresponding ‘ADD_SFCI command reply’ have same cmdID;
    PS2: Class TestBase and TestSimulatorBase has many useful function;

Usage of this unit test:
    python -m pytest ./test_addDelSFCI.py -s --disable-warnings
'''

import logging
import time
import uuid

import pytest

from sam.base.compatibility import screenInput
from sam.base.messageAgent import DISPATCHER_QUEUE, \
    MEDIATOR_QUEUE, SIMULATOR_ZONE
from sam.base.command import CMD_TYPE_ADD_SFC, CMD_TYPE_ADD_SFCI, CMD_TYPE_DEL_SFC, CMD_TYPE_DEL_SFCI
from sam.base.request import REQUEST_TYPE_ADD_SFC, REQUEST_TYPE_ADD_SFCI, REQUEST_TYPE_DEL_SFC, REQUEST_TYPE_DEL_SFCI, Request
from sam.base.shellProcessor import ShellProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.simulator.test.testSimulatorBase import TestSimulatorBase

MANUAL_TEST = True


class TestAddSFCClass(TestSimulatorBase):
    def common_setup(self):
        logConfigur = LoggerConfigurator(__name__, './log',
                                            'testAddSFCClass.log',
                                            level='debug')
        logConfigur = LoggerConfigurator(__name__, './log',
            'testAddSFCClass.log', level='info')
        self.logger = logConfigur.getLogger()

        # setup
        self.sP = ShellProcessor()
        self.cleanLog()
        self.clearQueue()
        self.killAllModule()
        time.sleep(3)
        self.mediator = MediatorStub()
        self.logger.info("Please start dispatcher! Then press Any key to continue!")
        screenInput()

    @pytest.fixture(scope="function")
    def setup_addOneSFC(self):
        self.common_setup()

        # you can overwrite following function to test different sfc/sfci
        classifier = None
        self.sfc = self.genUniDirectionSFC(classifier)
        self.sfci = self.genUniDirection10BackupSFCI(mappedVNFISeq=False)

        yield

        # teardown
        self.clearQueue()
        self.killAllModule()

    @pytest.mark.skip(reason='Skip temporarily')
    def test_addOneSFCWithVNFIOnAServer(self, setup_addOneSFC):
        # exercise
        rq = Request(uuid.uuid1(), uuid.uuid1(), REQUEST_TYPE_ADD_SFC,
            attributes={
                "sfc": self.sfc,
                "zone": SIMULATOR_ZONE
            })
        self.sendRequest(DISPATCHER_QUEUE, rq)

        # verify
        self.verifyAddSFCCmdRply()

        # exercise
        rq = Request(uuid.uuid1(), uuid.uuid1(), REQUEST_TYPE_ADD_SFCI,
            attributes={
                "sfc": self.getSFCFromDB(),
                # "sfc": self.sfc,
                "sfci": self.sfci,
                "zone": SIMULATOR_ZONE
            })
        self.sendRequest(DISPATCHER_QUEUE, rq)

        # verify
        self.verifyAddSFCICmdRply()

    def verifyAddSFCCmdRply(self):
        cmd = self.recvCmd(MEDIATOR_QUEUE)
        self.logger.info("Mediator recv cmd: {0}".format(cmd))
        assert cmd.cmdType == CMD_TYPE_ADD_SFC

    def verifyAddSFCICmdRply(self):
        cmd = self.recvCmd(MEDIATOR_QUEUE)
        self.logger.info("Mediator recv cmd: {0}".format(cmd))
        assert cmd.cmdType == CMD_TYPE_ADD_SFCI

    def getSFCFromDB(self):
        self._oib = OrchInfoBaseMaintainer("localhost", "dbAgent", "123",
                                            False)
        self.sfcInDB = self._oib.getSFC4DB(self.sfc.sfcUUID)
        return self.sfcInDB

    @pytest.fixture(scope="function")
    def setup_delOneSFC(self):
        self.common_setup()

        # you can overwrite following function to test different sfc/sfci
        classifier = None
        self.sfc = self.genUniDirectionSFC(classifier)
        self.sfci = self.genUniDirection10BackupSFCI(mappedVNFISeq=False)

        yield

        # teardown
        self.clearQueue()
        self.killAllModule()

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_delOneSFCWithVNFIOnAServer(self, setup_delOneSFC):
        # exercise
        rq = Request(uuid.uuid1(), uuid.uuid1(), REQUEST_TYPE_ADD_SFC,
            attributes={
                "sfc": self.sfc,
                "zone": SIMULATOR_ZONE
            })
        self.sendRequest(DISPATCHER_QUEUE, rq)

        # verify
        self.verifyAddSFCCmdRply()

        # exercise
        rq = Request(uuid.uuid1(), uuid.uuid1(), REQUEST_TYPE_ADD_SFCI,
            attributes={
                "sfc": self.getSFCFromDB(),
                # "sfc": self.sfc,
                "sfci": self.sfci,
                "zone": SIMULATOR_ZONE
            })
        self.sendRequest(DISPATCHER_QUEUE, rq)

        # verify
        self.verifyAddSFCICmdRply()

        # exercise
        rq = Request(uuid.uuid1(), uuid.uuid1(), REQUEST_TYPE_DEL_SFCI,
            attributes={
                "sfc": self.getSFCFromDB(),
                # "sfc": self.sfc,
                "sfci": self.sfci,
                "zone": SIMULATOR_ZONE
            })
        self.sendRequest(DISPATCHER_QUEUE, rq)

        # verify
        self.verifyDelSFCICmdRply()

        # exercise
        rq = Request(uuid.uuid1(), uuid.uuid1(), REQUEST_TYPE_DEL_SFC,
            attributes={
                "sfc": self.getSFCFromDB(),
                "zone": SIMULATOR_ZONE
            })
        self.sendRequest(DISPATCHER_QUEUE, rq)

        # verify
        self.verifyDelSFCCmdRply()

    def verifyDelSFCICmdRply(self):
        cmd = self.recvCmd(MEDIATOR_QUEUE)
        self.logger.info("Mediator recv cmd: {0}".format(cmd))
        assert cmd.cmdType == CMD_TYPE_DEL_SFCI

    def verifyDelSFCCmdRply(self):
        cmd = self.recvCmd(MEDIATOR_QUEUE)
        self.logger.info("Mediator recv cmd: {0}".format(cmd))
        assert cmd.cmdType == CMD_TYPE_DEL_SFC
