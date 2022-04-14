#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid
import time
import logging

import pytest
from sam.base.shellProcessor import ShellProcessor
from sam.base.messageAgent import SERVER_CLASSIFIER_CONTROLLER_QUEUE, \
    MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, SFF_CONTROLLER_QUEUE, MEDIATOR_QUEUE, \
    MSG_TYPE_SFF_CONTROLLER_CMD, MSG_TYPE_SFF_CONTROLLER_CMD, \
    NETWORK_CONTROLLER_QUEUE, MSG_TYPE_NETWORK_CONTROLLER_CMD
from sam.base.command import CMD_STATE_SUCCESSFUL
from sam.test.testBase import TestBase, CLASSIFIER_DATAPATH_IP
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.test.fixtures.vnfControllerStub import VNFControllerStub

logging.basicConfig(level=logging.INFO)


class TestUFRRClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_addUniSFCI(self):
        # setup
        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genUniDirectionSFC(classifier)
        self.sfci = self.genUniDirection11BackupSFCI()
        self.mediator = MediatorStub()
        self.vC = VNFControllerStub()
        self.sP = ShellProcessor()
        self.clearQueue()
        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc,self.sfci)

        # add SFCI to classifier
        logging.info("setup add SFCI to classifier")
        self.runClassifierController()
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SERVER_CLASSIFIER_CONTROLLER_QUEUE,
            MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, self.addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

        # add SFCI to SFF
        logging.info("setup add SFCI to sff")
        self.runSFFController()
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SFF_CONTROLLER_QUEUE,
            MSG_TYPE_SFF_CONTROLLER_CMD , self.addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

        # add VNFI to server
        logging.info("setup add SFCI to server")
        self.addVNFI2Server()

        yield
        # teardown
        self.delVNFI4Server()
        self.killClassifierController()
        self.killSFFController()

    def addVNFI2Server(self):
        try:
            # In normal case, there should be a timeout error!
            shellCmdRply = self.vC.installVNF("t1", "123", "192.168.122.134",
                self.sfci.vnfiSequence[0][0].vnfiID)
            logging.info("command reply:\n stdin:{0}\n stdout:{1}\n stderr:{2}".format(
                None,
                shellCmdRply['stdout'].read().decode('utf-8'),
                shellCmdRply['stderr'].read().decode('utf-8')))
        except:
            logging.info("If raise IOError: reading from stdin while output is captured")
            logging.info("Then pytest should use -s option!")
        try:
            # In normal case, there should be a timeout error!
            shellCmdRply = self.vC.installVNF("t1", "123", "192.168.122.208",
                self.sfci.vnfiSequence[0][1].vnfiID)
            logging.info("command reply:\n stdin:{0}\n stdout:{1}\n stderr:{2}".format(
                None,
                shellCmdRply['stdout'].read().decode('utf-8'),
                shellCmdRply['stderr'].read().decode('utf-8')))
        except:
            logging.info("If raise IOError: reading from stdin while output is captured")
            logging.info("Then pytest should use -s option!")

    def delVNFI4Server(self):
        self.vC.uninstallVNF("t1", "123", "192.168.122.134",
                    self.sfci.vnfiSequence[0][0].vnfiID)
        self.vC.uninstallVNF("t1", "123", "192.168.122.208",
                    self.sfci.vnfiSequence[0][1].vnfiID)
        time.sleep(10)
        # Here has a unstable bug
        # In sometimes, we can't delete VNFI, you should delete it manually
        # Command: sudo docker stop name1

    # @pytest.mark.skip(reason='Temporarly')
    def test_UFRRAddUniSFCI(self, setup_addUniSFCI):
        logging.info("You need start ryu-manager and mininet manually!"
            "Then press any key to continue!")
        raw_input()  # type: ignore
        # exercise
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(NETWORK_CONTROLLER_QUEUE,
            MSG_TYPE_NETWORK_CONTROLLER_CMD,
            self.addSFCICmd)

        # verify
        logging.info("Start listening on mediator queue")
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        logging.info("Press any key to quit!")
        raw_input()  # type: ignore

    @pytest.fixture(scope="function")
    def setup_delUniSFCI(self):
        # setup
        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genUniDirectionSFC(classifier)
        self.sfci = self.genUniDirection11BackupSFCI()
        self.mediator = MediatorStub()
        self.vC = VNFControllerStub()
        self.sP = ShellProcessor()
        self.clearQueue()
        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc,self.sfci)

        # add SFCI to classifier
        logging.info("setup add SFCI to classifier")
        self.runClassifierController()
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SERVER_CLASSIFIER_CONTROLLER_QUEUE,
            MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, self.addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

        # add SFCI to SFF
        logging.info("setup add SFCI to sff")
        self.runSFFController()
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SFF_CONTROLLER_QUEUE,
            MSG_TYPE_SFF_CONTROLLER_CMD , self.addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

        self.delSFCICmd = self.mediator.genCMDDelSFCI(self.sfc,self.sfci)
        yield
        # teardown
        self.killClassifierController()
        self.killSFFController()

    @pytest.mark.skip(reason='Temporarly')
    def test_UFRRDelUniSFCI(self, setup_delUniSFCI):
        logging.info("You need start ryu-manager and mininet manually!"
            "Then press any key to continue!")
        raw_input()  # type: ignore
        # exercise
        logging.info("Sending add SFCI command to ryu")
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(NETWORK_CONTROLLER_QUEUE,
            MSG_TYPE_NETWORK_CONTROLLER_CMD,
            self.addSFCICmd)
        logging.info("Start listening on mediator queue")
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

        logging.info("Ready to send delete SFCI command to ryu"
                "Press any key to continue!")
        raw_input()  # type: ignore
        self.delSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(NETWORK_CONTROLLER_QUEUE,
            MSG_TYPE_NETWORK_CONTROLLER_CMD,
            self.delSFCICmd)
        # verify
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL


    @pytest.fixture(scope="function")
    def setup_addBiSFCI(self):
        # setup
        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        self.sfc = self.genBiDirectionSFC(classifier)
        self.sfci = self.genBiDirection10BackupSFCI()
        self.mediator = MediatorStub()
        self.sP = ShellProcessor()
        self.clearQueue()
        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc,self.sfci)
        yield
        # teardown

    @pytest.mark.skip(reason='Temporarly')
    def test_UFRRAddBiSFCI(self, setup_addBiSFCI):
        # exercise 
        self.sendCmd(NETWORK_CONTROLLER_QUEUE,
            MSG_TYPE_NETWORK_CONTROLLER_CMD,
            self.addSFCICmd)

        # verify
        logging.info("Start listening on mediator queue")
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def printVNFISequence(self, vnfiSequence):
        for vnf in vnfiSequence:
            for vnfi in vnf:
                logging.info(
                    "vnfID:{0},vnfiID:{1}".format(
                        vnfi.vnfID,vnfi.vnfiID))