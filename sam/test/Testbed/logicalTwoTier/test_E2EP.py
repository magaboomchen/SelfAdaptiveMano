#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
Before state test, please run ch17/ufrr/logicalTwoTier/init_bridge.sh in pica8-switch1 and pica8-switch2
'''

import sys
import time
import logging
import copy

import pytest
from ryu.controller import dpset

from sam import base
from sam.ryu.topoCollector import TopoCollector
from sam.base.path import *
from sam.base.vnf import *
from sam.base.pickleIO import *
from sam.base.shellProcessor import ShellProcessor
from sam.test.testBase import *
from sam.test.fixtures.vnfControllerStub import *
from sam.test.Testbed.logicalTwoTier.testbedFRR import *
from sam.orchestration.oSFCAdder import *
from sam.measurement.dcnInfoBaseMaintainer import *

logging.basicConfig(level=logging.INFO)
logging.getLogger("pika").setLevel(logging.WARNING)

# TODO
# 首先人工检查每个sfci，查看e2e是否有无法保护的case：有很多都无法保护，没关系。
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
        # setup
        self.resetRabbitMQConf(
            base.__file__[:base.__file__.rfind("/")] + "/rabbitMQConf.conf",
            "192.168.0.194", "mq", "123456")
        self.sP = ShellProcessor()
        self.cleanLog()
        self.clearQueue()
        self.killAllModule()

        logConfigur = LoggerConfigurator(__name__, './log',
            'testE2EProtectionClass.log', level='info')
        self.logger = logConfigur.getLogger()

        self._messageAgent = MessageAgent()
        self.zoneName = PICA8_ZONE
        self.mediator = MediatorStub()
        self.pIO = PickleIO()

        self.loadInstance()
        self.loadSolution()
        self._dib = DCNInfoBaseMaintainer()
        self._updateDib()
        self.oSA = OSFCAdder(self._dib, self.logger)
        self.oSA.zoneName = PICA8_ZONE
        self.makeCmdList(self.e2eProtectionSolution)

        # self.runServerManager()
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
            sfc = addSFCICmd.attributes['sfc']
            sfc.vNFTypeSequence = [VNF_TYPE_FORWARD]

    def _makeAddSFCCmdList(self):
        self.addSFCCmdList = []
        for index, RequestAddSFCICmdTuple in enumerate(self.requestAddSFCICmdTupleList):
            addSFCICmd = RequestAddSFCICmdTuple[1]
            addSFCCmd = copy.deepcopy(addSFCICmd)
            addSFCCmd.cmdType = CMD_TYPE_ADD_SFC
            addSFCCmd.attributes.pop('sfci')
            self.addSFCCmdList.append(addSFCCmd)

    def _makeAddSFCICmdList(self):
        self.addSFCICmdList = []
        for index, RequestAddSFCICmdTuple in enumerate(self.requestAddSFCICmdTupleList):
            addSFCICmd = copy.deepcopy(RequestAddSFCICmdTuple[1])
            self.addSFCICmdList.append(addSFCICmd)

    def _makeDelSFCICmdList(self):
        self.delSFCICmdList = []
        for index, RequestAddSFCICmdTuple in enumerate(self.requestAddSFCICmdTupleList):
            addSFCICmd = RequestAddSFCICmdTuple[1]
            delSFCICmd = copy.deepcopy(addSFCICmd)
            delSFCICmd.cmdType = CMD_TYPE_DEL_SFCI
            self.delSFCICmdList.append(delSFCICmd)

    def test_addUniSFCI(self, setup_addUniSFCI):
        self.logger.info("You need to start ryu-manager manually!"
            "Then press any key to continue!")
        raw_input()

        self.addSFCIs()

        self.logger.info("Please input any key to test "
            "server software failure\n"
            "After the test, "
            "Press any key to quit!")
        raw_input()
        self.sendHandleServerSoftwareFailureCmd()

        self.logger.info("Press any key to quit!")
        raw_input()

    def addSFCIs(self):
        for index, addSFCCmd in enumerate(self.addSFCCmdList):
            self.addSFCCmd = self.addSFCCmdList[index]
            self.addSFCICmd = self.addSFCICmdList[index]
            self.addSFCI2Classifier()
            # self.addSFCI2SFF()
            # self.addVNFI2Server()
            # self.logger.warning(self.addSFCCmd)
            # raw_input()
            self.addSFC2NetworkController()
            self.addSFCI2NetworkController()
            break

    def delSFCIs(self):
        for index, delSFCICmd in enumerate(self.delSFCICmdList):
            self.delSFCICmd = self.delSFCICmdList[index]
            self.delSFCI2Classifier()
            # self.delSFCI2SFF()
            # self.delVNFI4Server()
            break

    def sendHandleServerSoftwareFailureCmd(self):
        #TODO: 找一个承载SFCI最多的服务器来执行宕机测试
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
        self._messageAgent.sendMsg(NETWORK_CONTROLLER_QUEUE, msg)
