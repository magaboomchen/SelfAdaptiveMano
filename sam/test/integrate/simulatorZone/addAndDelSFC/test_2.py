#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is an example for writing integrate test
The work flow:
    * generate 5 addSFC and 5 addSFCI command to dispatcher
    * get dcn info from measurer and print interest info

Usage of this unit test:
    sudo python -m pytest ./test_2.py -s --disable-warnings
'''

import uuid
import logging

import pytest

from sam.base.compatibility import screenInput
from sam.base.messageAgent import DISPATCHER_QUEUE, SIMULATOR_ZONE
from sam.base.request import REQUEST_TYPE_ADD_SFC, REQUEST_TYPE_ADD_SFCI, \
                        REQUEST_TYPE_DEL_SFC, REQUEST_TYPE_DEL_SFCI, Request
from sam.test.integrate.simulatorZone.addAndDelSFC.intTestBase import IntTestBaseClass

MANUAL_TEST = True


class TestAddSFCClass(IntTestBaseClass):
    @pytest.fixture(scope="function")
    def setup_manySFCs(self):
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

    def test_fiveSFCs(self, setup_manySFCs):
        # exercise
        for idx, sfc in enumerate(self.sfcList):
            rq = Request(uuid.uuid1(), uuid.uuid1(), REQUEST_TYPE_ADD_SFC,
                attributes={
                    "sfc": sfc,
                    "zone": SIMULATOR_ZONE
                })
            self.sendRequest(DISPATCHER_QUEUE, rq)

        logging.info("Please check orchestrator if recv a command reply?"\
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
            logging.info("sfc is {0}".format(sfc))
            self.sendRequest(DISPATCHER_QUEUE, rq)

            logging.info("Please check orchestrator if recv a command reply?"\
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

        logging.info("Please check orchestrator if recv a command reply?"\
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

        logging.info("Please check orchestrator if recv a command reply?"\
                        "Then press andy key to continue!")
        screenInput()
