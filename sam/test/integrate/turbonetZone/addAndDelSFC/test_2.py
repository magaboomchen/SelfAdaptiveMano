#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is an example for writing integrate test
The work flow:
    * generate 5 addSFC and 5 addSFCI command to dispatcher
    * get dcn info from measurer and print interest info

Usage of this unit test:
    python -m pytest ./test_2.py -s --disable-warnings
'''

import uuid

import pytest

from sam.base.compatibility import screenInput
from sam.base.messageAgent import DISPATCHER_QUEUE, TURBONET_ZONE
from sam.base.request import REQUEST_TYPE_ADD_SFC, REQUEST_TYPE_ADD_SFCI, \
                        REQUEST_TYPE_DEL_SFC, REQUEST_TYPE_DEL_SFCI, Request
from sam.test.integrate.intTestBase import IntTestBaseClass


class TestAddSFCClass(IntTestBaseClass):
    @pytest.fixture(scope="function")
    def setup_manySFCs(self):
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
                    "zone": TURBONET_ZONE
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
                    "zone": TURBONET_ZONE
                })
            self.logger.info("sfc is {0}".format(sfc))
            self.sendRequest(DISPATCHER_QUEUE, rq)

        self.logger.info("Please check orchestrator if recv a command reply?"\
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
            self.sendRequest(DISPATCHER_QUEUE, rq)

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
            self.sendRequest(DISPATCHER_QUEUE, rq)

        self.logger.info("Please check orchestrator if recv a command reply?"\
                        "Then press andy key to continue!")
        screenInput()
