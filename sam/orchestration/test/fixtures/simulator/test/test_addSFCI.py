#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is an example for writing test of simulator
Note:
    Unit test for simulator's add sfci handler;
    Mediator sends command to simulator;
    Simulator processes the command and then send back a command reply to mediator;
    The command and the corresponding command reply have same cmdID;
    Some type of command has content stored in cmd.attributes such as CMD_TYPE_GET_TOPOLOGY;
    Here are some format of attributes:
        CMD_TYPE_GET_SERVER_SET:
            attributes = {'servers': self.serverSet}    # see server.py
        CMD_TYPE_GET_TOPOLOGY:
            attributes = {
                "switches": self.switches,  # see switch.py
                "links": self.links,    # see link.py
            }
        CMD_TYPE_GET_SFCI_STATE:
            attributes = {
                "vnfis": self.vnfis   # see vnf.py, store state in vnfi.vnfiStatus
                "sfci": self.sfci   # see sfc.py, store state in sfci.sloRealTimeValue
            }
    Class TestBase has many useful function;
'''

import pytest

from sam.base.messageAgent import SIMULATOR_QUEUE, MSG_TYPE_SIMULATOR_CMD, \
    MEDIATOR_QUEUE
from sam.base.command import CMD_STATE_SUCCESSFUL
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.test.testBase import TestBase, CLASSIFIER_DATAPATH_IP


class TestAddSFCIClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_addSFCI(self):
        # setup
        self.clearQueue()
        self.mediator = MediatorStub()

        # you can overwrite following function to test different sfc/sfci
        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genBiDirectionSFC(classifier)
        self.sfci = self.genBiDirection10BackupSFCI()

        yield
        # teardown
        pass

    # @pytest.mark.skip(reason='Skip temporarily')
    def test_addSFCI(self, setup_addSFCI):
        # exercise
        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.sfci)
        self.sendCmd(SIMULATOR_QUEUE, MSG_TYPE_SIMULATOR_CMD , self.addSFCICmd)

        # verify
        self.verifyCmdRply()

    def verifyCmdRply(self):
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
