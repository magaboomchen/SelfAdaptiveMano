#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
import time
import logging
import copy

import pytest
from ryu.controller import dpset

from sam import base
from sam.ryu.topoCollector import TopoCollector
from sam.base.path import *
from sam.base.pickleIO import *
from sam.base.shellProcessor import ShellProcessor
from sam.test.testBase import *
from sam.test.fixtures.vnfControllerStub import *
from sam.test.Testbed.logicalTwoTier.testbedFRR import *
from sam.orchestration.oSFCAdder import *

logging.basicConfig(level=logging.INFO)
logging.getLogger("pika").setLevel(logging.WARNING)

# TODO
# 首先人工检查每个sfci，查看e2e是否有无法保护的case：
# 读取addSFCIcmdlist.pickle
# 然后做简单的测试：
# 实现函数发送所有的cmd, 监听cmdrply。
# 如果100条都成功部署。
# 再测试正常情况下的每条服务链的datapath是否ping通。
# 接着做几个故障情境下的测试。
# 最后跑出吞吐量的图和时延的图。


class TestE2EProtectionClass(TestbedFRR):
    @pytest.fixture(scope="function")
    def setup_addUniSFCI(self):
        logConfigur = LoggerConfigurator(__name__, './log',
            'testE2EProtectionClass.log', level='debug')
        self.logger = logConfigur.getLogger()

        # setup
        self.resetRabbitMQConf(
            base.__file__[:base.__file__.rfind("/")] + "/rabbitMQConf.conf",
            "192.168.0.194", "mq", "123456")
        self.sP = ShellProcessor()
        self.clearQueue()
        self.killAllModule()

        self._messageAgent = MessageAgent()
        self.mediator = MediatorStub()
        self.pIO = PickleIO()
        self.oSA = OSFCAdder(None, self.logger)

        self.loadInstance()
        self.loadSolution()
        self.makeCmdList(self.e2eProtectionSolution)
        return

        self.runServerManager()
        self.runClassifierController()
        self.runSFFController()
        self.runVNFController()

        yield
        # teardown
        self.delSFCIs()
        self.killClassifierController()
        self.killSFFController()
        self.killVNFController()
        self.killServerManager()

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

    # def makeCmdList(self, forwardingPathSetDict):
        # self.addSFCCmdList = []
        # self.addSFCICmdList = []
        # self.delSFCICmdList = []
        # for index, addSFCIRequest in enumerate(self.addSFCIRequests):
        #     self.logger.debug("addSFCIRequest: {0}".format(addSFCIRequest))
        #     sfc = addSFCIRequest.attributes['sfc']
        #     addSFCCmd = self.mediator.genCMDAddSFC(sfc)
        #     self.addSFCCmdList.append(addSFCCmd)

        #     sfci = addSFCIRequest.attributes['sfci']
        #     forwardingPathSet = forwardingPathSetDict[index]
        #     sfci.forwardingPathSet = 
        #     addSFCICmd = self.mediator.genCMDAddSFCI(sfc, sfci)
        #     self.addSFCICmdList.append(addSFCICmd)

        #     sfci = addSFCIRequest.attributes['sfci']
        #     delSFCICmd = self.mediator.genCMDDelSFCI(sfc, sfci)
        #     self.delSFCICmdList.append(delSFCICmd)

    def makeCmdList(self, forwardingPathSetDict):
        self.addSFCICmdList = []
        self.addSFCICmdList.extend(
            self.oSA._forwardingPathSetsDict2Cmd(forwardingPathSetDict,
                                                    self.addSFCIRequests)
        )

        self.delSFCICmdList = []
        for index, addSFCICmd in enumerate(self.addSFCICmdList):
            delSFCICmd = copy.deepcopy(addSFCICmd)
            delSFCICmd.cmdType = CMD_TYPE_DEL_SFCI
            self.delSFCICmdList.append(delSFCICmd)

    def test_addUniSFCI(self, setup_addUniSFCI):
        logging.info("You need to start ryu-manager manually!"
            "Then press any key to continue!")
        raw_input()

        self.addSFCIs()

        logging.info("Please input any key to test "
            "server software failure\n"
            "After the test, "
            "Press any key to quit!")
        raw_input()
        self.sendHandleServerSoftwareFailureCmd()

        logging.info("Press any key to quit!")
        raw_input()

    def addSFCIs(self):
        for index, addSFCCmd in enumerate(self.addSFCCmdList):
            self.addSFCCmd = self.addSFCCmdList[index]
            self.addSFCICmd = self.addSFCICmdList[index]
            self.addSFCI2Classifier()
            self.addSFCI2SFF()
            self.addVNFI2Server()
            self.addSFC2NetworkController()
            self.addSFCI2NetworkController()

    def sendHandleServerSoftwareFailureCmd(self):
        #TODO: 找一个承载SFCI最多的服务器来执行宕机测试
        logging.info("sendHandleServerFailureCmd")
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
        self._messageAgent.sendMsg(NETWORK_CONTROLLER_QUEUE, msg)

    def delSFCIs(self):
        for index, delSFCICmd in enumerate(self.delSFCICmdList):
            self.delSFCICmd = self.delSFCICmdList[index]
            self.delSFCI2Classifier()
            self.delSFCI2SFF()
            self.delVNFI4Server()
