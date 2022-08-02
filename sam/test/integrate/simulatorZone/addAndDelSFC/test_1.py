#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is an example for writing integrate test
The work flow:
    * generate 1 addSFC and 1 addSFCI command to dispatcher

Usage of this unit test:
    python -m pytest ./test_1.py -s --disable-warnings
'''

import uuid

import pytest

from sam.base.compatibility import screenInput
from sam.base.messageAgent import DISPATCHER_QUEUE, SIMULATOR_ZONE
from sam.base.request import REQUEST_TYPE_ADD_SFC, REQUEST_TYPE_ADD_SFCI, \
                        REQUEST_TYPE_DEL_SFC, REQUEST_TYPE_DEL_SFCI, Request
from sam.test.integrate.intTestBase import IntTestBaseClass

MANUAL_TEST = True


class TestAddSFCClass(IntTestBaseClass):
    @pytest.fixture(scope="function")
    def setup_oneSFC(self):
        self.common_setup()

        # you can overwrite following function to test different sfc/sfci
        classifier = None
        self.sfc = self.genLargeBandwidthSFC(classifier)
        self.sfci = self.genSFCITemplate()

        yield

        # teardown
        self.common_teardown()

    def test_oneSFC(self, setup_oneSFC):
        # exercise
        rq = Request(uuid.uuid1(), uuid.uuid1(), REQUEST_TYPE_ADD_SFC,
            attributes={
                "sfc": self.sfc,
                "zone": SIMULATOR_ZONE
            })
        self.sendRequest(DISPATCHER_QUEUE, rq)

        self.logger.info("Please check orchestrator if recv a command reply?"\
                        "Then press andy key to continue!")
        screenInput()

        # exercise
        sfcInDB = self.getSFCFromDB(self.sfc.sfcUUID)
        self.logger.info("sfcInDB is {0}".format(sfcInDB))
        rq = Request(uuid.uuid1(), uuid.uuid1(), REQUEST_TYPE_ADD_SFCI,
            attributes={
                "sfc": sfcInDB,
                "sfci": self.sfci,
                "zone": SIMULATOR_ZONE
            })
        self.sendRequest(DISPATCHER_QUEUE, rq)

        self.logger.info("Please check orchestrator if recv a command reply?"\
                        "Then press andy key to continue!")
        screenInput()

        # exercise
        rq = Request(uuid.uuid1(), uuid.uuid1(), REQUEST_TYPE_DEL_SFCI,
            attributes={
                "sfc": self.getSFCFromDB(self.sfc.sfcUUID),
                "sfci": self.sfci,
                "zone": SIMULATOR_ZONE
            })
        self.sendRequest(DISPATCHER_QUEUE, rq)

        self.logger.info("Please check orchestrator if recv a command reply?"\
                        "Then press andy key to continue!")
        screenInput()

        # exercise
        rq = Request(uuid.uuid1(), uuid.uuid1(), REQUEST_TYPE_DEL_SFC,
            attributes={
                "sfc": self.getSFCFromDB(self.sfc.sfcUUID),
                "zone": SIMULATOR_ZONE
            })
        self.sendRequest(DISPATCHER_QUEUE, rq)

        self.logger.info("Please check orchestrator if recv a command reply?"\
                        "Then press andy key to continue!")
        screenInput()
