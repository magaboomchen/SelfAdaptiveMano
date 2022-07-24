#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This is an example for writing integrate test
The work flow:
    * generate 1 addSFC and 1 addSFCI command to dispatcher

Usage of this unit test:
    python -m pytest ./test_notice.py -s --disable-warnings
'''

import time
import uuid
import logging

import pytest

from sam.base.compatibility import screenInput
from sam.base.messageAgent import DISPATCHER_QUEUE, MSG_TYPE_REGULATOR_CMD, REGULATOR_QUEUE, SIMULATOR_ZONE, TURBONET_ZONE
from sam.base.path import MAPPING_TYPE_NETPACK, ForwardingPathSet
from sam.base.request import REQUEST_TYPE_ADD_SFCI, REQUEST_TYPE_DEL_SFCI
from sam.base.server import SERVER_TYPE_NFVI, Server
from sam.base.sfc import APP_TYPE_LARGE_BANDWIDTH, SFC, SFCI, STATE_ACTIVE
from sam.base.shellProcessor import ShellProcessor
from sam.base.slo import SLO
from sam.base.switch import SWITCH_TYPE_DCNGATEWAY, Switch
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.path import MAPPING_TYPE_NETPACK, ForwardingPathSet
from sam.base.command import CMD_TYPE_HANDLE_FAILURE_ABNORMAL, Command
from sam.base.vnf import VNF_TYPE_MONITOR, VNF_TYPE_RATELIMITER, VNFI, VNFI_RESOURCE_QUOTA_SMALL
from sam.base.request import REQUEST_TYPE_ADD_SFCI, REQUEST_TYPE_DEL_SFCI
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer
from sam.base.messageAgent import DISPATCHER_QUEUE, REGULATOR_QUEUE, \
                                    SIMULATOR_ZONE
from sam.simulator.test.testSimulatorBase import SFF1_CONTROLNIC_IP, \
    SFF1_CONTROLNIC_MAC, SFF1_DATAPATH_IP, SFF1_DATAPATH_MAC, SFF1_SERVERID
from sam.test.Testbed.triangleTopo.testbedFRR import SFF2_DATAPATH_IP
from sam.test.fixtures.dispatcherStub import DispatcherStub
from sam.test.testBase import APP1_REAL_IP, SFF2_CONTROLNIC_IP, \
        SFF2_CONTROLNIC_MAC, SFF2_DATAPATH_MAC, SFF2_SERVERID, TestBase

MANUAL_TEST = True


class TestNoticeClass(TestBase):
    def common_setup(self):
        logConfigur = LoggerConfigurator(__name__, './log',
                                            'testNoticeClass.log',
                                            level='debug')
        self.logger = logConfigur.getLogger()
        self.logger.setLevel(logging.DEBUG)
        self._oib = OrchInfoBaseMaintainer("localhost", "dbAgent", "123",
                                            True)

        # setup
        self.sP = ShellProcessor()
        self.cleanRequestAndSFCAndSFCITableInDB()
        self.cleanLog()
        self.clearQueue()
        self.killAllModule()
        self.dispatcherStub = DispatcherStub()

    @pytest.fixture(scope="function")
    def setup_OneSFC(self):
        self.common_setup()

        # you can overwrite following function to test different sfc/sfci
        classifier = Switch(0, SWITCH_TYPE_DCNGATEWAY)
        self.sfc = self.genLargeBandwidthSFC(classifier)
        self.sfci = self.genUniDirection10BackupSFCI()

        self.storeSFC2DB(self.sfc)
        self.storeSFCI2DB(self.sfci, self.sfc.sfcUUID, self.sfc.attributes["zone"])
        self.updateSFCIState2DB(self.sfci, STATE_ACTIVE)
        yield

        # teardown
        self.delSFC4DB(self.sfc)
        self.delSFCI4DB(self.sfci)
        self.killAllModule()
        time.sleep(2)
        self.clearQueue()

    def genLargeBandwidthSFC(self, classifier):
        sfcUUID = uuid.uuid1()
        vNFTypeSequence = [VNF_TYPE_MONITOR, VNF_TYPE_RATELIMITER]
        maxScalingInstanceNumber = 1
        backupInstanceNumber = 0
        applicationType = APP_TYPE_LARGE_BANDWIDTH
        direction1 = {
            'ID': 0,
            'source': {'node': None, 'IPv4':"*"},
            'ingress': classifier,
            'match': {'srcIP': "*",'dstIP':APP1_REAL_IP,
                'srcPort': "*",'dstPort': "*",'proto': "*"},
            'egress': classifier,
            'destination': {'node': None, 'IPv4':APP1_REAL_IP}
        }
        directions = [direction1]
        slo = SLO(throughput=10, latency=100, availability=0.999, \
                    connections=10)
        return SFC(sfcUUID, vNFTypeSequence, maxScalingInstanceNumber,
            backupInstanceNumber, applicationType, directions,
            {'zone': SIMULATOR_ZONE}, slo=slo, vnfiResourceQuota=VNFI_RESOURCE_QUOTA_SMALL)

    def genUniDirection10BackupSFCI(self):
        vnfiSequence = self.genLargeBandwidthVNFISequence()
        return SFCI(self.assignSFCIID(), vnfiSequence, None,
            self.genUniDirection10BackupForwardingPathSet())

    def genLargeBandwidthVNFISequence(self):
        # hard-code function
        vnfiSequence = [[],[]]

        server = Server("ens3", SFF1_DATAPATH_IP, SERVER_TYPE_NFVI)
        server.setServerID(SFF1_SERVERID)
        server.setControlNICIP(SFF1_CONTROLNIC_IP)
        server.setControlNICMAC(SFF1_CONTROLNIC_MAC)
        server.setDataPathNICMAC(SFF1_DATAPATH_MAC)
        vnfi = VNFI(VNF_TYPE_MONITOR, vnfType=VNF_TYPE_MONITOR,
            vnfiID=uuid.uuid1(), node=server)
        vnfiSequence[0].append(vnfi)

        server = Server("ens3", SFF2_DATAPATH_IP, SERVER_TYPE_NFVI)
        server.setServerID(SFF2_SERVERID)
        server.setControlNICIP(SFF2_CONTROLNIC_IP)
        server.setControlNICMAC(SFF2_CONTROLNIC_MAC)
        server.setDataPathNICMAC(SFF2_DATAPATH_MAC)
        vnfi = VNFI(VNF_TYPE_RATELIMITER, vnfType=VNF_TYPE_RATELIMITER,
            vnfiID=uuid.uuid1(), node=server)
        vnfiSequence[1].append(vnfi)

        return vnfiSequence

    def genUniDirection10BackupForwardingPathSet(self):
        primaryForwardingPath = {
            1:[
                [(0,0),(0,256),(0,768),(0,SFF1_SERVERID)],
                [(1,SFF1_SERVERID),(1,SFF1_SERVERID)],
                [(2,SFF1_SERVERID),(2,768),(2,256),(2,0)]
            ]
        }
        mappingType = MAPPING_TYPE_NETPACK
        backupForwardingPath = {}
        return ForwardingPathSet(primaryForwardingPath, mappingType,
                                    backupForwardingPath)

    def storeSFC2DB(self, sfc):
        self._oib.addSFC2DB(sfc)

    def storeSFCI2DB(self, sfci, sfcUUID, zoneName):
        self._oib.addSFCI2DB(sfci, sfcUUID, zoneName)

    def delSFC4DB(self, sfc):
        self._oib.pruneSFC4DB(sfc.sfcUUID)

    def delSFCI4DB(self, sfci):
        self._oib.pruneSFCI4DB(sfci.sfciID)

    def updateSFCIState2DB(self, sfci, sfciState=STATE_ACTIVE):
        self._oib.updateSFCIState(sfci.sfciID, sfciState)

    def genAbnormalServerHandleCommand(self):
        detectionDict = {
            "failure":{
                "switchIDList":[],
                "serverIDList":[],
                "linkIDList":[]
            },
            "abnormal":{
                "switchIDList":[],
                "serverIDList":[SFF1_SERVERID],
                "linkIDList":[]
            }
        }
        allZoneDetectionDict={TURBONET_ZONE: detectionDict,  SIMULATOR_ZONE: detectionDict}
        attr = {
            "allZoneDetectionDict": allZoneDetectionDict
        }
        cmd = Command(CMD_TYPE_HANDLE_FAILURE_ABNORMAL, uuid.uuid1(), attributes=attr)
        return cmd

    def genFailureSwitchHandleCommand(self):
        detectionDict = {
            "failure":{
                "switchIDList":[256],
                "serverIDList":[],
                "linkIDList":[]
            },
            "abnormal":{
                "switchIDList":[],
                "serverIDList":[],
                "linkIDList":[]
            }
        }
        allZoneDetectionDict={TURBONET_ZONE: detectionDict,  SIMULATOR_ZONE: detectionDict}
        attr = {
            "allZoneDetectionDict": allZoneDetectionDict
        }
        cmd = Command(CMD_TYPE_HANDLE_FAILURE_ABNORMAL, uuid.uuid1(), attributes=attr)
        return cmd

    def test_abnormal(self, setup_OneSFC):
        # self.logger.info("Please turn on regulator,"\
        #                 "Then press andy key to continue!")
        # screenInput()
        self.runRegulator()

        # exercise
        # send command
        cmd = self.genAbnormalServerHandleCommand()
        self.sendCmd(REGULATOR_QUEUE, MSG_TYPE_REGULATOR_CMD, cmd)

        # check dispatcherStub
        req = self.recvRequest(DISPATCHER_QUEUE)
        assert req.requestType == REQUEST_TYPE_DEL_SFCI
        assert req.attributes["sfci"].sfciID == self.sfci.sfciID

        req = self.recvRequest(DISPATCHER_QUEUE)
        assert req.requestType == REQUEST_TYPE_ADD_SFCI
        assert req.attributes["sfci"].sfciID == self.sfci.sfciID

    def test_failure(self, setup_OneSFC):
        # self.logger.info("Please turn on regulator,"\
        #                 "Then press andy key to continue!")
        # screenInput()
        self.runRegulator()

        # exercise
        # send command
        cmd = self.genFailureSwitchHandleCommand()
        self.sendCmd(REGULATOR_QUEUE, MSG_TYPE_REGULATOR_CMD, cmd)

        # check dispatcherStub
        req = self.recvRequest(DISPATCHER_QUEUE)
        assert req.requestType == REQUEST_TYPE_DEL_SFCI
        assert req.attributes["sfci"].sfciID == self.sfci.sfciID

        req = self.recvRequest(DISPATCHER_QUEUE)
        assert req.requestType == REQUEST_TYPE_ADD_SFCI
        assert req.attributes["sfci"].sfciID == self.sfci.sfciID
