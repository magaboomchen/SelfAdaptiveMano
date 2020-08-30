import sys
import time

import pytest
from ryu.controller import dpset

from sam.ryu.topoCollector import TopoCollector
from sam.base.shellProcessor import ShellProcessor
from sam.test.testBase import *
from sam.test.fixtures.vnfControllerStub import *


class TestNotViaClass(TestBase):
    def genUniDirection10BackupSFCI(self):
        VNFISequence = self.gen10BackupVNFISequence()
        return SFCI(self.assignSFCIID(),VNFISequence, None,
            self.genUniDirection10BackupForwardingPathSet())

    def genUniDirection10BackupForwardingPathSet(self):
        primaryForwardingPath = {1:[[10001,1,2,10002],[10002,2,1,10001]]}
        frrType = "NotVia"
        # {(srcID,dstID,pathID):forwardingPath}
        backupForwardingPath = {
            1:{
                (1,2,2):[[1,3,2]],
                (2,1,3):[[2,3,1]],
            }
        }
        return ForwardingPathSet(primaryForwardingPath,frrType,
            backupForwardingPath)

    @pytest.fixture(scope="function")
    def setup_addUniSFCI(self):
        # setup
        classifier = self.genClassifier(datapathIfIP = SFF1_DATAPATH_IP)
        self.sfc = self.genUniDirectionSFC(classifier)
        self.sfci = self.genUniDirection10BackupSFCI()
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
            MSG_TYPE_SSF_CONTROLLER_CMD, self.addSFCICmd)
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

    def delVNFI4Server(self):
        self.vC.uninstallVNF("t1", "123", "192.168.122.134",
                    self.sfci.VNFISequence[0][0].VNFIID)
        # Here has a unstable bug
        # In sometimes, we can't delete VNFI, you should delete it manually
        # Command: sudo docker stop name1

    @pytest.mark.skip(reason='Temporarly')
    def test_NotViaAddUniSFCI(self, setup_addUniSFCI):
        print("You need start ryu-manager and mininet manually!\n"
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
        self.sfci = self.genUniDirection10BackupSFCI()
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

    # @pytest.mark.skip(reason='Temporarly')
    def test_NotViaDelUniSFCI(self, setup_delUniSFCI):
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