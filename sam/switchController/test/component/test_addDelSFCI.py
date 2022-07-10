#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is the test for p4 controller
The work flow:
    * Mediator sends ‘ADD_SFCI command’ to p4 controller;
    * P4 controller processes the command and then send back a command reply to the mediator;
    PS1:The ‘ADD_SFCI command’ and the corresponding ‘ADD_SFCI command reply’ have same cmdID;
    PS2: Class TestBase and IntTestBaseClass has many useful function;

Usage of this unit test:
    python -m pytest ./test_addDelSFCI.py -s --disable-warnings
'''

import logging
from time import sleep

import pytest

from sam.base.messageAgent import MSG_TYPE_P4CONTROLLER_CMD, P4CONTROLLER_QUEUE
from sam.switchController.test.component.p4ControllerTestBase import TestP4ControllerBase

MANUAL_TEST = True


class TestAddSFCIClass(TestP4ControllerBase):
    @pytest.fixture(scope="function")
    def setup_addSFCIWithP4VNFIOnASwitch(self):
        self.common_setup()

        logging.info("Please start P4Controller," \
                    "Then press any key to continue!")
        sleep(1)

        yield
        # teardown
        self.clearQueue()
        self.killAllModule()

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_addSFCIWithP4VNFIOnASwitch(self, 
                                        setup_addSFCIWithP4VNFIOnASwitch):
        self.exerciseAddSFCAndSFCI()



    @pytest.fixture(scope="function")
    def setup_delSFCIWithVNFIOnAServer(self):
        self.common_setup()

        logging.info("Please start P4Controller," \
                    "Then press any key to continue!")
        sleep(1)

        self.exerciseAddSFCAndSFCI()

        yield
        # teardown
        self.clearQueue()
        self.killAllModule()

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_delSFCIWithVNFIOnAServer(self,
                                            setup_delSFCIWithVNFIOnAServer):
        # exercise
        self.exerciseDelSFCAndSFCI()

    def exerciseDelSFCAndSFCI(self):
        for idx in [0,1,2]:
            logging.info("test idx {0}".format(idx))
            # exercise
            self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfcList[idx],
                                                        self.sfciList[idx])
            self.sendCmd(P4CONTROLLER_QUEUE, MSG_TYPE_P4CONTROLLER_CMD,
                                                self.addSFCICmd)

            # verify
            self.verifyAddSFCICmdRply()
