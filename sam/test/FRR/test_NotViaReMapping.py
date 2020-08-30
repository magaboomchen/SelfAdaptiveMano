import sys
import time

import pytest
from ryu.controller import dpset

from sam.ryu.topoCollector import TopoCollector
from sam.base.shellProcessor import ShellProcessor
from sam.test.testBase import *
from sam.test.fixtures.vnfControllerStub import *


class TestNotViaAndReMappingClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_addUniSFCI(self):
        # setup
        self.sP = ShellProcessor()
        self.clearQueue()

        classifier = self.genClassifier(datapathIfIP = SFF1_DATAPATH_IP)
        self.sfc = self.genUniDirectionSFC(classifier)
        self.sfci = self.genUniDirection11BackupSFCI()
        self.SFCIID = self.sfci.SFCIID
        self.VNFISequence = self.sfci.VNFISequence
        self.newSfci = self.genReMappingUniDirection11BackupSFCI(self.SFCIID, self.VNFISequence)

        self.mediator = MediatorStub()
        self.addSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.sfci)
        self.delSFCICmd = self.mediator.genCMDDelSFCI(self.sfc, self.sfci)
        self.reAddSFCICmd = self.mediator.genCMDAddSFCI(self.sfc, self.newSfci)

        self.runClassifierController()
        self.addSFCI2Classifier()

        self.runSFFController()
        self.addSFCI2SFF()

        self.vC = VNFControllerStub()
        self.addVNFI2Server()

        yield
        # teardown
        self.delVNFI4Server()
        self.delSFCI2SFF()
        self.delSFCI2Classifier()
        self.killClassifierController()
        self.killSFFController()

    def clearQueue(self):
        self.sP.runShellCommand("sudo rabbitmqctl purge_queue MEDIATOR_QUEUE")
        self.sP.runShellCommand(
            "sudo rabbitmqctl purge_queue NETWORK_CONTROLLER_QUEUE")
        self.sP.runShellCommand(
            "sudo rabbitmqctl purge_queue SFF_CONTROLLER_QUEUE")
        self.sP.runShellCommand(
            "sudo rabbitmqctl purge_queue SERVER_CLASSIFIER_CONTROLLER_QUEUE")
        self.sP.runShellCommand(
            "sudo rabbitmqctl purge_queue MININET_TESTER_QUEUE")

    def genUniDirection11BackupForwardingPathSet(self):
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

    def genReMappingUniDirection11BackupSFCI(self, SFCIID, VNFISequence):
        return SFCI(SFCIID,VNFISequence, None,
            self.genNewUniDirection11BackupForwardingPathSet())

    def genNewUniDirection11BackupForwardingPathSet(self):
        primaryForwardingPath = {1:[[10001,1,3,10003],[10003,3,1,10001]]}
        frrType = "NotVia"
        # {(srcID,dstID,pathID):forwardingPath}
        backupForwardingPath = {
            1:{
                (1,3,2):[[1,2,3]],
                (3,1,3):[[3,2,1]]
            }
        }
        return ForwardingPathSet(primaryForwardingPath,frrType,
            backupForwardingPath)

    def addSFCI2Classifier(self):
        print("setup add SFCI to classifier")
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SERVER_CLASSIFIER_CONTROLLER_QUEUE,
            MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, self.addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def addSFCI2SFF(self):
        print("setup add SFCI to sff")
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SFF_CONTROLLER_QUEUE,
            MSG_TYPE_SSF_CONTROLLER_CMD , self.addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def delSFCI2Classifier(self):
        print("teardown delete SFCI to classifier")
        self.delSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SERVER_CLASSIFIER_CONTROLLER_QUEUE,
            MSG_TYPE_CLASSIFIER_CONTROLLER_CMD, self.delSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def delSFCI2SFF(self):
        print("teardown delete SFCI to sff")
        self.delSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(SFF_CONTROLLER_QUEUE,
            MSG_TYPE_SSF_CONTROLLER_CMD , self.delSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def addVNFI2Server(self):
        print("setup add SFCI to server")
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
        print("teardown del SFCI from server")
        self.vC.uninstallVNF("t1", "123", "192.168.122.134",
                    self.sfci.VNFISequence[0][0].VNFIID)
        self.vC.uninstallVNF("t1", "123", "192.168.122.208",
                    self.sfci.VNFISequence[0][1].VNFIID)
        time.sleep(10)
        # Here is a bug
        print("Sometimes, we can't delete VNFI, you should delete it manually"
            "Command: sudo docker stop name1"
            )

    # @pytest.mark.skip(reason='Temporarly')
    def test_addUniSFCI(self, setup_addUniSFCI):
        print("You need start ryu-manager and mininet manually!"
            "Then press any key to continue!")
        raw_input()
        # exercise: mapping SFCI
        self.addSFCICmd.cmdID = uuid.uuid1()
        self.sendCmd(NETWORK_CONTROLLER_QUEUE,
            MSG_TYPE_NETWORK_CONTROLLER_CMD,
            self.addSFCICmd)

        # verify
        print("Start listening on mediator queue")
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

        # exercise: remapping SFCI
        print("Start listening on MININET_TESTER_QUEUE"
            "Please run mode 1 in mininet test2.py")
        cmd = self.recvCmd(MININET_TESTER_QUEUE)
        if cmd.cmdType == CMD_TYPE_TESTER_REMAP_SFCI:
            # exercise
            print("Start remapping the sfci")
            self.delSFCICmd.cmdID = uuid.uuid1()
            self.sendCmd(NETWORK_CONTROLLER_QUEUE,
                MSG_TYPE_NETWORK_CONTROLLER_CMD,
                self.delSFCICmd)

            # verify
            print("Start listening on mediator queue")
            cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
            assert cmdRply.cmdID == self.delSFCICmd.cmdID
            assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

            # exercise
            self.reAddSFCICmd.cmdID = uuid.uuid1()
            self.sendCmd(NETWORK_CONTROLLER_QUEUE,
                MSG_TYPE_NETWORK_CONTROLLER_CMD,
                self.reAddSFCICmd)

            # verify
            print("Start listening on mediator queue")
            cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
            assert cmdRply.cmdID == self.reAddSFCICmd.cmdID
            assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        else:
            print("cmdType:{0}".format(cmd.cmdType))

        print("Press any key to quit!")
        raw_input()
