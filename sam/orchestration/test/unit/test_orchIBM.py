#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid
import logging
from datetime import datetime

import pytest
import pickle
import base64

from sam.base.request import *
from sam.base.databaseAgent import DatabaseAgent
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer
from sam.test.testBase import *

MANUAL_TEST = True
logging.basicConfig(level=logging.INFO)


class TestOIBMClass(TestBase):
    @classmethod
    def setup_class(cls):
        """ setup any state specific to the execution of the given class (which
        usually contains tests).
        """
        logConfigur = LoggerConfigurator(__name__, './log',
            'testOIBM.log', level='debug')
        cls.logger = logConfigur.getLogger()

        cls.oib = OrchInfoBaseMaintainer("localhost", "dbAgent", "123")

        cls.testBase = TestBase()
        cls.classifier = cls.testBase.genClassifier("2.2.0.36")
        cls.sfc = cls.testBase.genUniDirectionSFC(cls.classifier)
        cls.sfci = SFCI(cls.testBase._genSFCIID(), [],
            ForwardingPathSet=ForwardingPathSet({},"UFRR",{}))

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

    def test_initRequestTable(self):
        self.oib._initRequestTable()
        assert self.oib.dbA.hasTable("Orchestrator", "Request") == True

    def test_initSFCTable(self):
        self.oib._initSFCTable()
        assert self.oib.dbA.hasTable("Orchestrator", "SFC") == True

    def test_initSFCITable(self):
        self.oib._initSFCITable()
        assert self.oib.dbA.hasTable("Orchestrator", "SFCI") == True

    def test_addRequest2DB(self):
        self.oib._addRequest2DB(self.addSFCRequest, self.addSFCCmd)
        condition = " REQUEST_UUID = '{0}' ".format(
            self.addSFCRequest.requestID)
        results = self.oib.dbA.query("Request", " * ",
            condition)
        assert results != ()

        self.oib._addRequest2DB(self.addSFCIRequest, self.addSFCICmd)
        condition = " REQUEST_UUID = '{0}' ".format(
            self.addSFCIRequest.requestID)
        results = self.oib.dbA.query("Request", " * ",
            condition)
        assert results != ()

        self.oib._addRequest2DB(self.delSFCIRequest, self.delSFCICmd)
        condition = " REQUEST_UUID = '{0}' ".format(
            self.delSFCIRequest.requestID)
        results = self.oib.dbA.query("Request", " * ",
            condition)
        assert results != ()

        self.oib._addRequest2DB(self.delSFCRequest, self.delSFCCmd)
        condition = " REQUEST_UUID = '{0}' ".format(
            self.delSFCRequest.requestID)
        results = self.oib.dbA.query("Request", " * ",
            condition)
        assert results != ()

    def test_getRequest(self):
        request = self.oib.getRequestByCmdID(self.addSFCCmd.cmdID)
        assert request.requestID == self.addSFCRequest.requestID

    def test_updateRequestState2DB(self):
        request = self.oib.getRequestByRequestUUID(self.addSFCRequest.requestID)
        assert request.requestState == REQUEST_STATE_INITIAL

        self.oib.updateRequestState2DB(self.addSFCRequest,
            REQUEST_STATE_SUCCESSFUL)
        
        request = self.oib.getRequestByRequestUUID(self.addSFCRequest.requestID)
        assert request.requestState == REQUEST_STATE_SUCCESSFUL

    def test_addSFC2DB(self):
        sfc = self.oib.getSFC4DB(self.sfc.sfcUUID)
        assert sfc == None
        self.oib._addSFC2DB(self.sfc)
        sfc = self.oib.getSFC4DB(self.sfc.sfcUUID)
        assert sfc.sfcUUID == self.sfc.sfcUUID

    def test_updateSFCState(self):
        state = self.oib._getSFCState(self.sfc.sfcUUID)
        assert state == STATE_IN_PROCESSING
        self.oib._updateSFCState(self.sfc.sfcUUID, STATE_INACTIVE)
        sfc = self.oib.getSFC4DB(self.sfc.sfcUUID)
        state = self.oib._getSFCState(self.sfc.sfcUUID)
        assert state == STATE_INACTIVE

    def test_addSFCI2SFCInDB(self):
        results = self.oib.dbA.query("SFC", " SFCIID_LIST ",
            " SFC_UUID = '{0}' ".format(self.sfc.sfcUUID))
        assert results[0][0] == ""
        self.oib._addSFCI2SFCInDB(self.sfc.sfcUUID, self.sfci.SFCIID)
        results = self.oib.dbA.query("SFC", " SFCIID_LIST ",
            " SFC_UUID = '{0}' ".format(self.sfc.sfcUUID))
        assert results[0][0] == str(self.sfci.SFCIID) + ","

    def test_delSFCI4SFCInDB(self):
        results = self.oib.dbA.query("SFC", " SFCIID_LIST ",
            " SFC_UUID = '{0}' ".format(self.sfc.sfcUUID))
        assert results[0][0] == str(self.sfci.SFCIID) + ","
        self.oib._delSFCI4SFCInDB(self.sfc.sfcUUID, self.sfci.SFCIID)
        results = self.oib.dbA.query("SFC", " SFCIID_LIST ",
            " SFC_UUID = '{0}' ".format(self.sfc.sfcUUID))
        assert results[0][0] == ""

    def test_addSFCI2DB(self):
        self.oib._addSFCI2DB(self.sfci)
        sfci = self.oib.getSFCI4DB(self.sfci.SFCIID)
        assert sfci.SFCIID == self.sfci.SFCIID

    def test_updateSFCIState(self):
        self.oib._updateSFCIState(self.sfci.SFCIID, STATE_DELETED)
        assert self.oib._getSFCIState(self.sfci.SFCIID) == STATE_DELETED

    def test_pruneSFC4DB(self):
        self.oib._pruneSFC4DB(self.sfc.sfcUUID)
        assert self.oib.getSFC4DB(self.sfc.sfcUUID) == None

    def test_pruneSFCI4DB(self):
        self.oib._pruneSFCI4DB(self.sfci.SFCIID)
        assert self.oib.getSFC4DB(self.sfci.SFCIID) == None
