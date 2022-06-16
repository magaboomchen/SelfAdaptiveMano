#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is an example for writing integrate test
The work flow:
    * generate 1 addSFC and 1 addSFCI command to dispatcher

Usage of this unit test:
    sudo python -m pytest ./test_1.py -s --disable-warnings
'''

import uuid
import logging

import pytest

from sam.base.messageAgent import DISPATCHER_QUEUE, SIMULATOR_ZONE
from sam.base.request import REQUEST_TYPE_ADD_SFC, REQUEST_TYPE_ADD_SFCI, REQUEST_TYPE_DEL_SFC, REQUEST_TYPE_DEL_SFCI, Request
from sam.test.integrate.simulatorZone.addAndDelSFC.intTestBase import IntTestBaseClass

MANUAL_TEST = True


class TestAddSFCClass(IntTestBaseClass):
    @pytest.fixture(scope="function")
    def setup_OneSFC(self):
        self.common_setup()

        # you can overwrite following function to test different sfc/sfci
        classifier = None
        self.sfc = self.genLargeBandwidthSFC(classifier)
        self.sfci = self.genSFCITemplate()

        yield

        # teardown
        self.clearQueue()
        self.killAllModule()

    def test_oneSFCWithVNFIOnAServer(self, setup_OneSFC):
        # exercise
        rq = Request(uuid.uuid1(), uuid.uuid1(), REQUEST_TYPE_ADD_SFC,
            attributes={
                "sfc": self.sfc,
                "zone": SIMULATOR_ZONE
            })
        self.sendRequest(DISPATCHER_QUEUE, rq)

        logging.info("Please check orchestrator if recv a command reply?"\
                        "Then press andy key to continue!")
        raw_input() # type: ignore

        # exercise
        rq = Request(uuid.uuid1(), uuid.uuid1(), REQUEST_TYPE_ADD_SFCI,
            attributes={
                "sfc": self.getSFCFromDB(self.sfc.sfcUUID),
                # "sfc": self.sfc,
                "sfci": self.sfci,
                "zone": SIMULATOR_ZONE
            })
        self.sendRequest(DISPATCHER_QUEUE, rq)

        logging.info("Please check orchestrator if recv a command reply?"\
                        "Then press andy key to continue!")
        raw_input() # type: ignore

        # exercise
        rq = Request(uuid.uuid1(), uuid.uuid1(), REQUEST_TYPE_DEL_SFCI,
            attributes={
                "sfc": self.getSFCFromDB(self.sfc.sfcUUID),
                # "sfc": self.sfc,
                "sfci": self.sfci,
                "zone": SIMULATOR_ZONE
            })
        self.sendRequest(DISPATCHER_QUEUE, rq)

        logging.info("Please check orchestrator if recv a command reply?"\
                        "Then press andy key to continue!")
        raw_input() # type: ignore

        # exercise
        rq = Request(uuid.uuid1(), uuid.uuid1(), REQUEST_TYPE_DEL_SFC,
            attributes={
                "sfc": self.getSFCFromDB(self.sfc.sfcUUID),
                "zone": SIMULATOR_ZONE
            })
        self.sendRequest(DISPATCHER_QUEUE, rq)

        logging.info("Please check orchestrator if recv a command reply?"\
                        "Then press andy key to continue!")
        raw_input() # type: ignore
