#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging
import time
import json
from scapy.all import *

import pytest

from sam.base.sfc import *
from sam.base.vnf import *
from sam.base.server import *
from sam.serverController.classifierController import *
from sam.base.command import *
from sam.base.socketConverter import *
from sam.test.testBase import *


MANUAL_TEST = True

TESTER_SERVER_DATAPATH_IP = "192.168.124.1"
TESTER_SERVER_DATAPATH_MAC = "fe:54:00:42:26:44"

logging.basicConfig(level=logging.INFO)


class TestSFC2JsonClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_addSFCI(self):
        # setup
        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genBiDirectionSFC(classifier)
        self.sfci = self.genBiDirection10BackupSFCI()
        yield
        # teardown
        pass

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_addSFC(self, setup_addSFCI):
        # exercise
        cmdDict = self.sfc.to_dict()
        cmdDict['cmdType'] = "CMD_TYPE_ADD_SFC"
        cmdDict['cmdID'] = uuid.uuid1()

        jsonStr = json.dumps(cmdDict, indent=4, default=str)
        print(jsonStr)

        assert 1==1

    def test_addSFCI(self, setup_addSFCI):
        # exercise
        cmdDict = self.sfci.to_dict()
        cmdDict['sfcUUID'] = str(self.sfc.sfcUUID)
        cmdDict['cmdType'] = "CMD_TYPE_ADD_SFCI"
        cmdDict['cmdID'] = uuid.uuid1()

        jsonStr = json.dumps(cmdDict, indent=4, default=str)
        print(jsonStr)

        assert 1==1

    def test_delSFCI(self, setup_addSFCI):
        cmdDict = {}
        cmdDict['sfciID'] = self.sfci.sfciID
        cmdDict['cmdType'] = "CMD_TYPE_DEL_SFCI"
        cmdDict['cmdID'] = uuid.uuid1()

        jsonStr = json.dumps(cmdDict, indent=4, default=str)
        # print(jsonStr)

        assert 1==1

    def test_delSFC(self, setup_addSFCI):
        cmdDict = {}
        cmdDict['sfcUUID'] = self.sfc.sfcUUID
        cmdDict['cmdType'] = "CMD_TYPE_DEL_SFC"
        cmdDict['cmdID'] = uuid.uuid1()

        jsonStr = json.dumps(cmdDict, indent=4, default=str)
        print(jsonStr)

        assert 1==1
