#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
import time
import logging

import pytest
from ryu.controller import dpset

from sam.ryu.topoCollector import TopoCollector
from sam.base.command import *
from sam.base.shellProcessor import ShellProcessor
from sam.base.messageAgent import *
from sam.mediator.mediator import *
from sam.test.testBase import *
from sam.test.fixtures.vnfControllerStub import *


class TestbedFRR(TestBase):
    def cleanLog(self):
        self.sP.runShellCommand("rm -rf ./log")

    def addSFCI2Classifier(self):
        self.logger.info("setup add SFCI to classifier")
        queueName = self._messageAgent.genQueueName(
            SERVER_CLASSIFIER_CONTROLLER_QUEUE, self.zoneName)
        self.sendCmd(queueName, MSG_TYPE_CLASSIFIER_CONTROLLER_CMD,
                        self.addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def delSFCI2Classifier(self):
        self.logger.info("teardown delete SFCI to classifier")
        queueName = self._messageAgent.genQueueName(
            SERVER_CLASSIFIER_CONTROLLER_QUEUE, self.zoneName)
        self.sendCmd(queueName, MSG_TYPE_CLASSIFIER_CONTROLLER_CMD,
                        self.delSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def addSFCI2SFF(self):
        self.logger.info("setup add SFCI to sff")
        queueName = self._messageAgent.genQueueName(
            SFF_CONTROLLER_QUEUE, self.zoneName)
        self.sendCmd(queueName, MSG_TYPE_SFF_CONTROLLER_CMD,
                        self.addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def delSFCI2SFF(self):
        self.logger.info("teardown delete SFCI to sff")
        queueName = self._messageAgent.genQueueName(
            SFF_CONTROLLER_QUEUE, self.zoneName)
        self.sendCmd(queueName, MSG_TYPE_SFF_CONTROLLER_CMD,
                        self.delSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def addVNFI2Server(self):
        queueName = self._messageAgent.genQueueName(
            VNF_CONTROLLER_QUEUE, self.zoneName)
        self.sendCmd(queueName, MSG_TYPE_VNF_CONTROLLER_CMD,
                        self.addSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def delVNFI4Server(self):
        self.logger.warning("Deleting VNFI")
        queueName = self._messageAgent.genQueueName(
            VNF_CONTROLLER_QUEUE, self.zoneName)
        self.sendCmd(queueName, MSG_TYPE_VNF_CONTROLLER_CMD,
                        self.delSFCICmd)
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.delSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def addSFC2NetworkController(self):
        queueName = self._messageAgent.genQueueName(
            NETWORK_CONTROLLER_QUEUE, self.zoneName)
        self.sendCmd(queueName,
                    MSG_TYPE_NETWORK_CONTROLLER_CMD,
                    self.addSFCCmd)
        # verify
        self.logger.info("Start listening on mediator queue")
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCCmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def addSFCI2NetworkController(self):
        queueName = self._messageAgent.genQueueName(
            NETWORK_CONTROLLER_QUEUE, self.zoneName)
        self.sendCmd(queueName,
                        MSG_TYPE_NETWORK_CONTROLLER_CMD,
                        self.addSFCICmd)
        # verify
        self.logger.info("Start listening on mediator queue")
        cmdRply = self.recvCmdRply(MEDIATOR_QUEUE)
        assert cmdRply.cmdID == self.addSFCICmd.cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL

    def addSFC2Mediator(self):
        self.logger.info("Adding SFC")
        self.sendCmd(MEDIATOR_QUEUE,
                        MSG_TYPE_MEDIATOR_CMD,
                        self.addSFCCmd)

    def addSFCI2Mediator(self):
        self.logger.info("Adding SFCI")
        self.sendCmd(MEDIATOR_QUEUE,
                        MSG_TYPE_MEDIATOR_CMD,
                        self.addSFCICmd)

    def delSFCIViaMediator(self):
        self.logger.info("Deleting SFCI")
        self.sendCmd(MEDIATOR_QUEUE,
                        MSG_TYPE_MEDIATOR_CMD,
                        self.delSFCICmd)

    def sendHandleServerSoftwareFailureCmd(self):
        self.logger.info("sendHandleServerFailureCmd")
        server = Server("ens3", SFF1_DATAPATH_IP, SERVER_TYPE_NFVI)
        server.setServerID(SFF1_SERVERID)
        server.setControlNICIP(SFF1_CONTROLNIC_IP)
        server.setControlNICMAC(SFF1_CONTROLNIC_MAC)
        server.setDataPathNICMAC(SFF1_DATAPATH_MAC)
        msg = SAMMessage(MSG_TYPE_NETWORK_CONTROLLER_CMD,
            Command(
                cmdType=CMD_TYPE_HANDLE_SERVER_STATUS_CHANGE,
                cmdID=uuid.uuid1(),
                attributes={"serverDown":[server]}
            )
        )
        queueName = self._messageAgent.genQueueName(
            NETWORK_CONTROLLER_QUEUE, self.zoneName)
        self._messageAgent.sendMsg(queueName, msg)

    def _updateDib(self):
        self._dib.updateServersByZone(self.topologyDict["servers"],
            PICA8_ZONE)
        self._dib.updateSwitchesByZone(self.topologyDict["switches"],
            PICA8_ZONE)
        self._dib.updateLinksByZone(self.topologyDict["links"],
            PICA8_ZONE)

        self._dib.updateSwitch2ServerLinksByZone(PICA8_ZONE)

    def runClassifierController(self):
        filePath = classifierControllerCommandAgent.__file__
        self.sP.runPythonScript(filePath+" "+PICA8_ZONE)

    def runSFFController(self):
        filePath = sffControllerCommandAgent.__file__
        self.sP.runPythonScript(filePath+" "+PICA8_ZONE)
    
    def runVNFController(self):
        filePath = vnfController.__file__
        self.sP.runPythonScript(filePath+" "+PICA8_ZONE)

    def runServerManager(self):
        filePath = serverManager.__file__
        self.sP.runPythonScript(filePath+" "+PICA8_ZONE)

    def loadInstance(self):
        instanceFilePath = "./LogicalTwoTier/0/LogicalTwoTier_n=3_k=3_V=6.sfcr_set_M=100.sfcLength=1.instance"
        self.instance = self.pIO.readPickleFile(instanceFilePath)
        self.topologyDict = self.instance['topologyDict']
        self.addSFCIRequests = self.instance['addSFCIRequests']

    def loadSolution(self):
        self.notViaPSFCSolutionFilePath \
            = "./LogicalTwoTier/0/LogicalTwoTier_n=3_k=3_V=6.sfcr_set_M=100.sfcLength=1.instance.NOTVIA_PSFC.solution"
        self.pSFCNotViaSolution = self.pIO.readPickleFile(
            self.notViaPSFCSolutionFilePath)

        self.e2ePSolutionFilePath \
            = "./LogicalTwoTier/0/LogicalTwoTier_n=3_k=3_V=6.sfcr_set_M=100.sfcLength=1.instance.E2EP.solution"
        self.e2eProtectionSolution = self.pIO.readPickleFile(
            self.e2ePSolutionFilePath)

        self.ufrrSolutionFilePath = solutionFileDir \
            = "./LogicalTwoTier/0/LogicalTwoTier_n=3_k=3_V=6.sfcr_set_M=100.sfcLength=1.instance.UFRR.solution"
        self.mmlSFCSolution = self.pIO.readPickleFile(
            self.ufrrSolutionFilePath)

    def makeCmdList(self, forwardingPathSetDict):
        self._makeRequestAddSFCICmdTupleList(forwardingPathSetDict)
        self._makeAddSFCCmdList()
        self._makeAddSFCICmdList()
        self._makeDelSFCICmdList()

    def _makeRequestAddSFCICmdTupleList(self, forwardingPathSetDict):
        self.requestAddSFCICmdTupleList = []
        self.requestAddSFCICmdTupleList.extend(
            self.oSA._forwardingPathSetsDict2Cmd(forwardingPathSetDict,
                                                    self.addSFCIRequests))
        for index, RequestAddSFCICmdTuple in enumerate(self.requestAddSFCICmdTupleList):
            addSFCICmd = RequestAddSFCICmdTuple[1]
            addSFCICmd.attributes['zone'] = PICA8_ZONE
            sfc = addSFCICmd.attributes['sfc']
            sfc.vNFTypeSequence = [VNF_TYPE_FORWARD] * len(sfc.vNFTypeSequence)
            sfc.attributes['zone'] = PICA8_ZONE
            sfci = addSFCICmd.attributes['sfci']
            vnfiSequence = sfci.vnfiSequence
            for vnfisList in vnfiSequence:
                for vnfi in vnfisList:
                    vnfi.vnfType = VNF_TYPE_FORWARD
                    vnfi.maxCPUNum = 1

    def _makeAddSFCCmdList(self):
        self.addSFCCmdList = []
        for index, RequestAddSFCICmdTuple in enumerate(self.requestAddSFCICmdTupleList):
            addSFCICmd = RequestAddSFCICmdTuple[1]
            addSFCCmd = copy.deepcopy(addSFCICmd)
            addSFCCmd.cmdType = CMD_TYPE_ADD_SFC
            addSFCCmd.cmdID = uuid.uuid1()
            addSFCCmd.attributes.pop('sfci')
            self.addSFCCmdList.append(addSFCCmd)

    def _makeAddSFCICmdList(self):
        self.addSFCICmdList = []
        for index, RequestAddSFCICmdTuple in enumerate(self.requestAddSFCICmdTupleList):
            addSFCICmd = copy.deepcopy(RequestAddSFCICmdTuple[1])
            addSFCICmd.cmdID = uuid.uuid1()
            self.addSFCICmdList.append(addSFCICmd)

    def _makeDelSFCICmdList(self):
        self.delSFCICmdList = []
        for index, RequestAddSFCICmdTuple in enumerate(self.requestAddSFCICmdTupleList):
            addSFCICmd = RequestAddSFCICmdTuple[1]
            delSFCICmd = copy.deepcopy(addSFCICmd)
            delSFCICmd.cmdType = CMD_TYPE_DEL_SFCI
            delSFCICmd.cmdID = uuid.uuid1()
            self.delSFCICmdList.append(delSFCICmd)

    def addExpectedCmdRply(self, cmd):
        if not self.expectedCmdRplyDict.has_key(cmd.cmdID):
            self.expectedCmdRplyDict[cmd.cmdID] = None
        else:
            self.logger.error("Duplicated cmdID")

    def recvAllCmdReplysFromMediator(self, totalCmdReplyNum):
        self.logger.info("totalCmdReplyNum: {0}".format(totalCmdReplyNum))
        for _ in range(totalCmdReplyNum):
            self.logger.info("recv {0}-th cmdReply".format(_))
            # cmdRply = self.recvCmdRply(ORCHESTRATOR_QUEUE)
            cmdRply = self.oS.recvCmdRply()
            self.expectedCmdRplyDict[cmdRply.cmdID] = cmdRply

            if self.hasGotAllCmdRply():
                self.logger.info("Got all cmd reply! total number is :{0}".format(
                    len(self.expectedCmdRplyDict)
                ))
                break
            else:
                if _ >= 0.98 * totalCmdReplyNum:
                    self.findUnRecvedCmdReply()

    def findUnRecvedCmdReply(self):
        for cmdID, value in self.expectedCmdRplyDict.items():
            if value == None:
                self.logger.warning("haven't recv cmdID {0}".format(cmdID))

    def hasGotAllCmdRply(self):
        for cmdID, value in self.expectedCmdRplyDict.items():
            if value == None:
                return False
        else:
            return True

    def verifyCmdViaMediator(self, cmd):
        if cmd.cmdID not in self.expectedCmdRplyDict:
            self.logger.error("Unknown cmd reply")
            assert True == False
        else:
            cmdRply = self.expectedCmdRplyDict[cmd.cmdID]
            assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
