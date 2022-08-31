#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
Usage:
python -m pytest ./test_orchIBM.py -s
'''

import uuid

import pytest
from sam.base.messageAgent import DEFAULT_ZONE

from sam.base.path import ForwardingPathSet, MAPPING_TYPE_UFRR
from sam.base.command import Command, CMD_TYPE_ADD_SFC, CMD_TYPE_ADD_SFCI, \
    CMD_TYPE_DEL_SFC, CMD_TYPE_DEL_SFCI
from sam.base.request import REQUEST_STATE_SUCCESSFUL, REQUEST_STATE_INITIAL
from sam.base.sfc import SFCI
from sam.base.sfcConstant import STATE_IN_PROCESSING, STATE_INACTIVE, STATE_DELETED
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer
from sam.test.testBase import TestBase


class TestOIBMClass(TestBase):
    @classmethod
    def setup_class(cls):
        """ setup any state specific to the execution of the given class (which
        usually contains tests).
        """
        logConfigur = LoggerConfigurator(__name__, './log',
            'testOIBM.log', level='debug')
        cls.logger = logConfigur.getLogger()

        cls.oib = OrchInfoBaseMaintainer("localhost", "dbAgent", "123", 
                                            reInitialTable=True)

        cls.testBase = TestBase()
        cls.classifier = cls.testBase.genClassifier("2.2.0.36")
        cls.sfc = cls.testBase.genUniDirectionSFC(cls.classifier)
        cls.sfci = SFCI(cls.testBase._genSFCIID(), [],
            forwardingPathSet=ForwardingPathSet({}, MAPPING_TYPE_UFRR, {}))

        cls.zoneName = ""

        cls.addSFCRequest = cls.testBase.genAddSFCRequest(cls.sfc)
        cls.addSFCCmd = Command(CMD_TYPE_ADD_SFC, uuid.uuid1(), attributes={
            'sfc':cls.sfc, 'zone':cls.zoneName})

        cls.addSFCIRequest = cls.testBase.genAddSFCIRequest(cls.sfc, cls.sfci)
        cls.addSFCICmd = Command(CMD_TYPE_ADD_SFCI, uuid.uuid1(), attributes={
            'sfc':cls.sfc, 'sfci':cls.sfci, 'zone':cls.zoneName})

        cls.delSFCIRequest = cls.testBase.genDelSFCIRequest(cls.sfc, cls.sfci)
        cls.delSFCICmd = Command(CMD_TYPE_DEL_SFCI, uuid.uuid1(), attributes={
            'sfc':cls.sfc, 'sfci':cls.sfci, 'zone':cls.zoneName})

        cls.delSFCRequest = cls.testBase.genDelSFCRequest(cls.sfc)
        cls.delSFCCmd = Command(CMD_TYPE_DEL_SFC, uuid.uuid1(), attributes={
            'sfc':cls.sfc, 'zone':cls.zoneName})

    @classmethod
    def teardown_class(cls):
        """ teardown any state that was previously setup with a call to
        setup_class.
        """
        cls.oib.dbA.dropTable("Request")
        cls.oib.dbA.dropTable("SFC")
        cls.oib.dbA.dropTable("SFCI")

    # @pytest.mark.skip(reason='Temporarly')
    def test_initRequestTable(self):
        self.oib._initRequestTable()
        assert self.oib.dbA.hasTable("Orchestrator", "Request") == True

    # @pytest.mark.skip(reason='Temporarly')
    def test_initSFCTable(self):
        self.oib._initSFCTable()
        assert self.oib.dbA.hasTable("Orchestrator", "SFC") == True

    # @pytest.mark.skip(reason='Temporarly')
    def test_initSFCITable(self):
        self.oib._initSFCITable()
        assert self.oib.dbA.hasTable("Orchestrator", "SFCI") == True

    # @pytest.mark.skip(reason='Temporarly')
    def test_addRequest(self):
        self.oib.addRequest(self.addSFCRequest)
        condition = " REQUEST_UUID = '{0}' ".format(
            self.addSFCRequest.requestID)
        results = self.oib.dbA.query("Request", " * ",
            condition)
        assert results != ()

    # @pytest.mark.skip(reason='Temporarly')
    def test_queryRequest(self):
        request = self.oib.getRequestByRequestUUID(
                            self.addSFCRequest.requestID)
        assert request.requestID == self.addSFCRequest.requestID

    # @pytest.mark.skip(reason='Temporarly')
    def test_addCmdInfo2Request(self):
        self.oib.addCmdInfo2Request(self.addSFCRequest, self.addSFCCmd)
        condition = " REQUEST_UUID = '{0}' ".format(
            self.addSFCRequest.requestID)
        results = self.oib.dbA.query("Request", " * ",
            condition)
        assert results != ()

        self.oib.addCmdInfo2Request(self.addSFCIRequest, self.addSFCICmd)
        condition = " REQUEST_UUID = '{0}' ".format(
            self.addSFCIRequest.requestID)
        results = self.oib.dbA.query("Request", " * ",
            condition)
        assert results != ()

        self.oib.addCmdInfo2Request(self.delSFCIRequest, self.delSFCICmd)
        condition = " REQUEST_UUID = '{0}' ".format(
            self.delSFCIRequest.requestID)
        results = self.oib.dbA.query("Request", " * ",
            condition)
        assert results != ()

        self.oib.addCmdInfo2Request(self.delSFCRequest, self.delSFCCmd)
        condition = " REQUEST_UUID = '{0}' ".format(
            self.delSFCRequest.requestID)
        results = self.oib.dbA.query("Request", " * ",
            condition)
        assert results != ()

    # @pytest.mark.skip(reason='Temporarly')
    def test_getRequest(self):
        request = self.oib.getRequestByCmdID(self.addSFCCmd.cmdID)
        assert request.requestID == self.addSFCRequest.requestID

    # @pytest.mark.skip(reason='Temporarly')
    def test_updateRequestState2DB(self):
        request = self.oib.getRequestByRequestUUID(self.addSFCRequest.requestID)
        assert request.requestState == REQUEST_STATE_INITIAL

        self.oib.updateRequestState2DB(self.addSFCRequest,
            REQUEST_STATE_SUCCESSFUL)
        
        request = self.oib.getRequestByRequestUUID(self.addSFCRequest.requestID)
        assert request.requestState == REQUEST_STATE_SUCCESSFUL

    # @pytest.mark.skip(reason='Temporarly')
    def test_addSFC2DB(self):
        sfc = self.oib.getSFC4DB(self.sfc.sfcUUID)
        assert sfc == None
        self.oib.addSFC2DB(self.sfc)
        sfc = self.oib.getSFC4DB(self.sfc.sfcUUID)
        assert sfc.sfcUUID == self.sfc.sfcUUID

    # @pytest.mark.skip(reason='Temporarly')
    def test_updateSFCState(self):
        state = self.oib.getSFCState(self.sfc.sfcUUID)
        assert state == STATE_IN_PROCESSING
        self.oib.updateSFCState(self.sfc.sfcUUID, STATE_INACTIVE)
        sfc = self.oib.getSFC4DB(self.sfc.sfcUUID)
        state = self.oib.getSFCState(self.sfc.sfcUUID)
        assert state == STATE_INACTIVE

    # @pytest.mark.skip(reason='Temporarly')
    def test_addSFCI2SFCInDB(self):
        sfciIDList = self.oib.getSFCIIDListOfASFC4DB(self.sfc.sfcUUID)
        assert type(sfciIDList) == list
        assert len(sfciIDList) == 0
        self.oib._addSFCI2SFCInDB(self.sfc.sfcUUID, self.sfci.sfciID)
        sfciIDList = self.oib.getSFCIIDListOfASFC4DB(self.sfc.sfcUUID)
        assert type(sfciIDList) == list
        assert len(sfciIDList) == 1

    # @pytest.mark.skip(reason='Temporarly')
    def test_delSFCI4SFCInDB(self):
        sfciIDList = self.oib.getSFCIIDListOfASFC4DB(self.sfc.sfcUUID)
        assert type(sfciIDList) == list
        assert len(sfciIDList) == 1
        self.oib._delSFCI4SFCInDB(self.sfc.sfcUUID, self.sfci.sfciID)
        sfciIDList = self.oib.getSFCIIDListOfASFC4DB(self.sfc.sfcUUID)
        assert type(sfciIDList) == list
        assert len(sfciIDList) == 0

    # @pytest.mark.skip(reason='Temporarly')
    def test_addSFCI2DB(self):
        self.oib.addSFCI2DB(self.sfci, self.sfc.sfcUUID, DEFAULT_ZONE)
        sfci = self.oib.getSFCI4DB(self.sfci.sfciID)
        assert sfci.sfciID == self.sfci.sfciID

    # @pytest.mark.skip(reason='Temporarly')
    def test_updateSFCIState(self):
        self.oib.updateSFCIState(self.sfci.sfciID, STATE_DELETED)
        assert self.oib.getSFCIState(self.sfci.sfciID) == STATE_DELETED

    # @pytest.mark.skip(reason='Temporarly')
    def test_pruneSFC4DB(self):
        self.oib.pruneSFC4DB(self.sfc.sfcUUID)
        assert self.oib.getSFC4DB(self.sfc.sfcUUID) == None

    # @pytest.mark.skip(reason='Temporarly')
    def test_pruneSFCI4DB(self):
        self.oib.pruneSFCI4DB(self.sfci.sfciID)
        assert self.oib.getSFC4DB(self.sfci.sfciID) == None
