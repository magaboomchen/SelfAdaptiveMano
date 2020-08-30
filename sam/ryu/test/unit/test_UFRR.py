import sys
import time

import pytest
from ryu.controller import dpset

from sam.ryu.topoCollector import TopoCollector
from sam.base.shellProcessor import ShellProcessor
from sam.test.testBase import *
from sam.test.fixtures.vnfControllerStub import *


class TestUFRRClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_addUniSFCI(self):
        # setup
        classifier = self.genClassifier(datapathIfIP = SFF1_DATAPATH_IP)
        self.sfc = self.genUniDirectionSFC(classifier)
        self.sfci = self.genUniDirection11BackupSFCI()
        self.mediator = MediatorStub()
        self.vC = VNFControllerStub()
        self.sP = ShellProcessor()
        self.sP.runShellCommand("sudo rabbitmqctl purge_queue MEDIATOR_QUEUE")
        self.sP.runShellCommand(
            "sudo rabbitmqctl purge_queue NETWORK_CONTROLLER_QUEUE")
        self.sP.runShellCommand(
            "sudo rabbitmqctl purge_queue SFF_CONTROLLER_QUEUE")
        self.sP.runShellCommand(
            "sudo rabbitmqctl purge_queue SERVER_CLASSIFIER_CONTROLLER_QUEUE")
        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc,self.sfci)

        # add SFCI to classifier
        print("setup add SFCI to classifier")
        self.runClassifierController()
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SERVER_CLASSIFIER_CONTROLLER_QUEUE,
            MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, self.addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

        # add SFCI to SFF
        print("setup add SFCI to sff")
        self.runSFFController()
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SFF_CONTROLLER_QUEUE,
            MSG_TYPE_SSF_CONTROLLER_CMD , self.addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

        # add VNFI to server
        print("setup add SFCI to server")
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
                self.sfci.VNFISequence[0][0].VNFIID, self.sfc.directions)
            print("command reply:\n stdin:{0}\n stdout:{1}\n stderr:{2}".format(
                None,
                shellCmdRply['stdout'].read().decode('utf-8'),
                shellCmdRply['stderr'].read().decode('utf-8')))
        except:
            print("If raise IOError: reading from stdin while output is captured")
            print("Then pytest should use -s option!")
        try:
            # In normal case, there should be a timeout error!
            shellCmdRply = self.vC.installVNF("t1", "123", "192.168.122.208",
                self.sfci.VNFISequence[0][1].VNFIID, self.sfc.directions)
            print("command reply:\n stdin:{0}\n stdout:{1}\n stderr:{2}".format(
                None,
                shellCmdRply['stdout'].read().decode('utf-8'),
                shellCmdRply['stderr'].read().decode('utf-8')))
        except:
            print("If raise IOError: reading from stdin while output is captured")
            print("Then pytest should use -s option!")

    def delVNFI4Server(self):
        self.vC.uninstallVNF("t1", "123", "192.168.122.134",
                    self.sfci.VNFISequence[0][0].VNFIID)
        self.vC.uninstallVNF("t1", "123", "192.168.122.208",
                    self.sfci.VNFISequence[0][1].VNFIID)
        time.sleep(10)
        # Here has a unstable bug
        # In sometimes, we can't delete VNFI, you should delete it manually
        # Command: sudo docker stop name1

    # @pytest.mark.skip(reason='Temporarly')
    def test_UFRRAddUniSFCI(self, setup_addUniSFCI):
        print("You need start ryu-manager and mininet manually!"
            "Then press any key to continue!")
        raw_input()
        # exercise
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(NETWORK_CONTROLLER_QUEUE,
            MSG_TYPE_NETWORK_CONTROLLER_CMD,
            self.addSFCICmd)

        # verify
        print("Start listening on mediator queue")
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        print("Press any key to quit!")
        raw_input()

    @pytest.fixture(scope="function")
    def setup_delUniSFCI(self):
        # setup
        classifier = self.genClassifier(datapathIfIP = SFF1_DATAPATH_IP)
        self.sfc = self.genUniDirectionSFC(classifier)
        self.sfci = self.genUniDirection11BackupSFCI()
        self.mediator = MediatorStub()
        self.vC = VNFControllerStub()
        self.sP = ShellProcessor()
        self.sP.runShellCommand("sudo rabbitmqctl purge_queue MEDIATOR_QUEUE")
        self.sP.runShellCommand(
            "sudo rabbitmqctl purge_queue NETWORK_CONTROLLER_QUEUE")
        self.sP.runShellCommand(
            "sudo rabbitmqctl purge_queue SFF_CONTROLLER_QUEUE")
        self.sP.runShellCommand(
            "sudo rabbitmqctl purge_queue SERVER_CLASSIFIER_CONTROLLER_QUEUE")
        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc,self.sfci)

        # add SFCI to classifier
        print("setup add SFCI to classifier")
        self.runClassifierController()
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SERVER_CLASSIFIER_CONTROLLER_QUEUE,
            MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, self.addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

        # add SFCI to SFF
        print("setup add SFCI to sff")
        self.runSFFController()
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SFF_CONTROLLER_QUEUE,
            MSG_TYPE_SSF_CONTROLLER_CMD , self.addSFCICmd)
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
        print("You need start ryu-manager and mininet manually!"
            "Then press any key to continue!")
        raw_input()
        # exercise
        print("Sending add SFCI command to ryu")
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(NETWORK_CONTROLLER_QUEUE,
            MSG_TYPE_NETWORK_CONTROLLER_CMD,
            self.addSFCICmd)
        print("Start listening on mediator queue")
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

        print("Ready to send delete SFCI command to ryu"
                "Press any key to continue!")
        raw_input()
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
        classifier = self.genClassifier(datapathIfIP = SFF1_DATAPATH_IP)
        self.sfc = self.genBiDirectionSFC(classifier)
        self.sfci = self.genBiDirection10BackupSFCI()
        self.mediator = MediatorStub()
        self.sP = ShellProcessor()
        self.sP.runShellCommand("sudo rabbitmqctl purge_queue MEDIATOR_QUEUE")
        self.sP.runShellCommand(
                "sudo rabbitmqctl purge_queue NETWORK_CONTROLLER_QUEUE")
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
        print("Start listening on mediator queue")
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def printVNFISequence(self, VNFISequence):
        for vnf in VNFISequence:
            for vnfi in vnf:
                print("VNFID:{0},VNFIID:{1}".format(vnfi.VNFID,vnfi.VNFIID))