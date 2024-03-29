#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
Usage:
    (1) sudo env "PATH=$PATH" python -m pytest ./test_vnfControllerAddVNFs.py -s --disable-warnings
    (2) Please run 'python  ./serverAgent.py  0000:07:00.0  enp1s0  nfvi  2.2.0.98 10001'
        on the NFVI running bess.
'''

import time
import uuid

import pytest
from scapy.all import sniff, AsyncSniffer, Raw, sendp
from scapy.layers.inet import IP, TCP
from scapy.contrib.nsh import NSH
from scapy.layers.inet6 import IPv6
from sam.base.compatibility import screenInput

from sam.base.messageAgentAuxillary.msgAgentRPCConf import MEASURER_IP, MEASURER_PORT, VNF_CONTROLLER_IP, VNF_CONTROLLER_PORT
from sam.base.vnfiStatus import VNFIStatus
from sam.base.rateLimiter import RateLimiterConfig
from sam.base.monitorStatistic import MonitorStatistics
from sam.base.sfcConstant import SFC_DIRECTION_0, SFC_DIRECTION_1
from sam.base.acl import ACLTable, ACLTuple, ACL_ACTION_ALLOW, ACL_PROTO_TCP
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.messageAgent import TURBONET_ZONE, VNF_CONTROLLER_QUEUE, \
    MSG_TYPE_VNF_CONTROLLER_CMD, SFF_CONTROLLER_QUEUE, \
    MSG_TYPE_SFF_CONTROLLER_CMD, MEDIATOR_QUEUE, MessageAgent
from sam.base.routingMorphic import IPV4_ROUTE_PROTOCOL, IPV6_ROUTE_PROTOCOL,\
                                    ROCEV1_ROUTE_PROTOCOL, SRV6_ROUTE_PROTOCOL
from sam.base.vnf import VNF_TYPE_MONITOR, VNF_TYPE_RATELIMITER, VNFI, \
                                                VNF_TYPE_FW
from sam.base.server import SERVER_TYPE_NFVI, Server
from sam.serverController.serverManager.serverManager import SERVERID_OFFSET
from sam.base.command import CMD_STATE_SUCCESSFUL
from sam.base.shellProcessor import ShellProcessor
from sam.serverController.sffController.sfcConfig import CHAIN_TYPE_NSHOVERETH, \
                                            CHAIN_TYPE_UFRR, DEFAULT_CHAIN_TYPE
from sam.test.fixtures.measurementStub import MeasurementStub
from sam.test.fixtures.mediatorStub import MediatorStub
from sam.base.test.fixtures.ipv4MorphicDict import ipv4MorphicDictTemplate
from sam.test.testBase import DIRECTION0_TRAFFIC_SPI, DIRECTION1_TRAFFIC_SPI, \
    OUTTER_CLIENT_IPV6, SFF1_CONTROLNIC_INTERFACE, WEBSITE_REAL_IPV6, TestBase, \
    WEBSITE_REAL_IP, OUTTER_CLIENT_IP, \
    CLASSIFIER_DATAPATH_IP, SFCI1_0_EGRESS_IP, SFCI1_1_EGRESS_IP, \
    SFF1_DATAPATH_IP, SFF1_DATAPATH_MAC, SFF1_CONTROLNIC_IP, SFF1_CONTROLNIC_MAC
from sam.serverController.sffController.test.component.testConfig import TESTER_SERVER_DATAPATH_IP, \
    TESTER_SERVER_DATAPATH_MAC, TESTER_DATAPATH_INTF
from sam.serverController.vnfController.test.fixtures.sendDirection0Traffic import DGID, sendDirection0Traffic
from sam.serverController.vnfController.test.fixtures.sendDirection1Traffic import sendDirection1Traffic


class TestVNFAddFW(TestBase):
    @pytest.fixture(scope="function")
    def setup_addVNFs(self):
        # setup
        logConfigur = LoggerConfigurator(__name__, './log',
            'tester.log', level='debug')
        self.logger = logConfigur.getLogger()
        self._messageAgent = MessageAgent(self.logger)

        self.sP = ShellProcessor()
        self.clearQueue()
        self.killAllModule()

        self.routeMorphic = IPV4_ROUTE_PROTOCOL
        self.server = self.genTesterServer(TESTER_SERVER_DATAPATH_IP,
                                            TESTER_SERVER_DATAPATH_MAC)
        self.sfcList = []
        self.sfciList = []

        classifier = self.genClassifier(datapathIfIP = CLASSIFIER_DATAPATH_IP)
        sfc1 = self.genBiDirectionSFC(classifier, vnfTypeSeq=[VNF_TYPE_FW],
                            routingMorphicTemplate=ipv4MorphicDictTemplate,
                            zone=TURBONET_ZONE)
        sfci1 = self.genBiDirection10BackupSFCI()


        sfc2 = self.genBiDirectionSFC(classifier, vnfTypeSeq=[VNF_TYPE_MONITOR],
                            routingMorphicTemplate=ipv4MorphicDictTemplate,
                            zone=TURBONET_ZONE)
        sfci2 = self.genBiDirection10BackupSFCI()


        sfc3 = self.genBiDirectionSFC(classifier, vnfTypeSeq=[VNF_TYPE_RATELIMITER],
                            routingMorphicTemplate=ipv4MorphicDictTemplate,
                            zone=TURBONET_ZONE)
        sfci3 = self.genBiDirection10BackupSFCI()


        # self.sfcList = [sfc1]
        # self.sfciList = [sfci1]

        # self.sfcList = [sfc1, sfc2]
        # self.sfciList = [sfci1, sfci2]

        self.sfcList = [sfc1, sfc2, sfc3]
        self.sfciList = [sfci1, sfci2, sfci3]

        self.mediator = MediatorStub()
        self.runSFFController()
        self.addSFCI2SFF()
        self.runVNFController()
        
        self.measurer = MeasurementStub()

        yield
        # teardown
        self.delVNFI4Server()
        self.killSFFController()
        self.killVNFController()

    def gen10BackupVNFISequence(self, SFCLength=1):
        # hard-code function
        vnfiSequence = []
        for index in range(SFCLength):
            vnfiSequence.append([])
            for iN in range(1):
                server = Server(SFF1_CONTROLNIC_INTERFACE, SFF1_DATAPATH_IP,
                                    SERVER_TYPE_NFVI)
                server.setServerID(SERVERID_OFFSET + 1)
                server.setControlNICIP(SFF1_CONTROLNIC_IP)
                server.setControlNICMAC(SFF1_CONTROLNIC_MAC)
                server.setDataPathNICMAC(SFF1_DATAPATH_MAC)
                server.updateResource()
                aclT = ACLTable()
                ipv4RulesList = self.genTestIPv4FWRules()
                for ipv4Rule in ipv4RulesList:
                    aclT.addRules(ipv4Rule, IPV4_ROUTE_PROTOCOL)
                ipv6RulesList = self.genTestIPv6FWRules()
                for ipv6Rule in ipv6RulesList:
                    aclT.addRules(ipv6Rule, IPV6_ROUTE_PROTOCOL)
                rocev1RulesList = self.genTestRoceV1FWRules()
                for rocev1Rule in rocev1RulesList:
                    aclT.addRules(rocev1Rule, ROCEV1_ROUTE_PROTOCOL)
                config = aclT
                vnfi = VNFI(VNF_TYPE_FW, vnfType=VNF_TYPE_FW, 
                    vnfiID=uuid.uuid1(), config=config, node=server)
                vnfiSequence[index].append(vnfi)
        return vnfiSequence

    def genTestIPv4FWRules(self):
        rules = []
        rules.append(ACLTuple(ACL_ACTION_ALLOW, proto=ACL_PROTO_TCP, srcAddr=OUTTER_CLIENT_IP, dstAddr=WEBSITE_REAL_IP, 
            srcPort=(1234, 1234), dstPort=(80, 80)))
        rules.append(ACLTuple(ACL_ACTION_ALLOW, proto=ACL_PROTO_TCP, srcAddr=WEBSITE_REAL_IP, dstAddr=OUTTER_CLIENT_IP,
            srcPort=(80, 80), dstPort=(1234, 1234)))
        rules.append(ACLTuple(ACL_ACTION_ALLOW))
        return rules

    def genTestIPv6FWRules(self):
        rules = []
        rules.append(ACLTuple(ACL_ACTION_ALLOW, dstAddr=WEBSITE_REAL_IPV6+"/128"))
        rules.append(ACLTuple(ACL_ACTION_ALLOW, dstAddr=OUTTER_CLIENT_IPV6+"/128"))
        rules.append(ACLTuple(ACL_ACTION_ALLOW))
        return rules

    def genTestRoceV1FWRules(self):
        rules = []
        rules.append(ACLTuple(ACL_ACTION_ALLOW, dstAddr=WEBSITE_REAL_IPV6+"/128"))
        rules.append(ACLTuple(ACL_ACTION_ALLOW, dstAddr=OUTTER_CLIENT_IPV6+"/128"))
        rules.append(ACLTuple(ACL_ACTION_ALLOW))
        return rules

    def addSFCI2SFF(self):
        for idx, sfc in enumerate(self.sfcList):
            self.logger.info("setup add SFCI to sff")
            self.addSFCICmd = self.mediator.genCMDAddSFCI(sfc, self.sfciList[idx])
            queueName = self._messageAgent.genQueueName(SFF_CONTROLLER_QUEUE, TURBONET_ZONE)
            self.sendCmd(queueName, MSG_TYPE_SFF_CONTROLLER_CMD, self.addSFCICmd)
            self.verifyCmdRply(MEDIATOR_QUEUE, self.addSFCICmd.cmdID)

    def delVNFI4Server(self):
        for idx, sfc in enumerate(self.sfcList):
            self.logger.warning("Deleting VNFI")
            self.delSFCICmd = self.mediator.genCMDDelSFCI(sfc, self.sfciList[idx])
            queueName = self._messageAgent.genQueueName(VNF_CONTROLLER_QUEUE, TURBONET_ZONE)
            self.sendCmd(queueName, MSG_TYPE_VNF_CONTROLLER_CMD, self.delSFCICmd)
            self.verifyCmdRply(MEDIATOR_QUEUE, self.delSFCICmd.cmdID)

    def test_addVNFs(self, setup_addVNFs):
        # exercise
        self.logger.info("exercise")
        for idx, sfc in enumerate(self.sfcList):
            self.addSFCICmd = self.mediator.genCMDAddSFCI(sfc, self.sfciList[idx])
            queueName = self._messageAgent.genQueueName(VNF_CONTROLLER_QUEUE, TURBONET_ZONE)
            self.sendCmd(queueName, MSG_TYPE_VNF_CONTROLLER_CMD, self.addSFCICmd)

            # verifiy
            self.verifyCmdRply(MEDIATOR_QUEUE, self.addSFCICmd.cmdID)
            self.spi = idx+1
            self.verifyDirection0Traffic(spi=self.spi)

            self.spi = 0x800000 | (idx+1)
            self.verifyDirection1Traffic(spi=self.spi)

        # exercise
        self.logger.info("exercise")
        self.getSFCIStateCmd = self.measurer.genCMDGetSFCIState()
        self.startMsgAgentRPCReciever(MEASURER_IP, MEASURER_PORT)
        self.sendCmdByRPC(VNF_CONTROLLER_IP, VNF_CONTROLLER_PORT,
                            MSG_TYPE_VNF_CONTROLLER_CMD, self.getSFCIStateCmd)

        # verifiy
        self.verifyGetSFCIStateCmdRply(MEASURER_IP, MEASURER_PORT, self.getSFCIStateCmd.cmdID)

    def verifyDirection0Traffic(self, spi):
        aSniffer = self._checkEncapsulatedTraffic(inIntf=TESTER_DATAPATH_INTF)
        time.sleep(2)
        sendDirection0Traffic(routeMorphic=self.routeMorphic, spi=spi)
        while True:
            if not aSniffer.running:
                break

    def _checkEncapsulatedTraffic(self,inIntf):
        self.logger.info("_checkEncapsulatedTraffic: wait for packet")
        filterRE = "ether dst " + str(self.server.getDatapathNICMac())
        # sniff(filter=filterRE,
        #     iface=inIntf, prn=self.encap_callback,count=1,store=0)
        aSniffer = AsyncSniffer(filter=filterRE,
            iface=inIntf, prn=self.encap_callback,count=1,store=0)
        aSniffer.start()
        return aSniffer

    def encap_callback(self, frame):
        self.logger.info("Get encap back packet!")
        frame.show()
        if DEFAULT_CHAIN_TYPE == CHAIN_TYPE_UFRR:
            condition = (frame[IP].src == SFF1_DATAPATH_IP \
                and frame[IP].dst == SFCI1_0_EGRESS_IP \
                and frame[IP].proto == 0x04)
            assert condition
            outterPkt = frame.getlayer('IP')[0]
            innerPkt = frame.getlayer('IP')[1]
            assert innerPkt[IP].dst == WEBSITE_REAL_IP
        elif DEFAULT_CHAIN_TYPE == CHAIN_TYPE_NSHOVERETH:
            condition = (frame[NSH].spi == self.spi \
                and frame[NSH].si == 0)
            assert condition == True
            if self.routeMorphic == IPV4_ROUTE_PROTOCOL:
                assert frame[NSH].nextproto == 0x1
                innerPkt = frame.getlayer('IP')[0]
                assert innerPkt[IP].dst == WEBSITE_REAL_IP
            elif self.routeMorphic in [IPV6_ROUTE_PROTOCOL, SRV6_ROUTE_PROTOCOL]:
                assert frame[NSH].nextproto == 0x2
                innerPkt = frame.getlayer('IPv6')[0]
                assert innerPkt[IPv6].dst == WEBSITE_REAL_IPV6
            elif self.routeMorphic == ROCEV1_ROUTE_PROTOCOL:
                assert frame[NSH].nextproto == 0x6
                # innerPkt = frame.getlayer('IPv6')[0]
                # assert innerPkt[GRH].dgid == DGID
            else:
                raise ValueError("Unknown nextproto.")
        else:
            raise ValueError("Unknown chain type {0}".format(DEFAULT_CHAIN_TYPE))

    def verifyDirection1Traffic(self, spi):
        aSniffer = self._checkDecapsulatedTraffic(inIntf=TESTER_DATAPATH_INTF)
        time.sleep(2)
        sendDirection1Traffic(routeMorphic=self.routeMorphic, spi=spi)
        while True:
            if not aSniffer.running:
                break

    def _checkDecapsulatedTraffic(self,inIntf):
        self.logger.info("_checkDecapsulatedTraffic: wait for packet")
        # sniff(filter="ether dst " + str(self.server.getDatapathNICMac()),
        #     iface=inIntf, prn=self.decap_callback,count=1,store=0)
        aSniffer = AsyncSniffer(filter="ether dst " + str(self.server.getDatapathNICMac()),
            iface=inIntf, prn=self.decap_callback,count=1,store=0)
        aSniffer.start()
        return aSniffer

    def decap_callback(self,frame):
        self.logger.info("Get decap back packet!")
        frame.show()
        if DEFAULT_CHAIN_TYPE == CHAIN_TYPE_UFRR:
            condition = (frame[IP].src == SFF1_DATAPATH_IP and \
                frame[IP].dst == SFCI1_1_EGRESS_IP and \
                frame[IP].proto == 0x04)
            assert condition == True
            outterPkt = frame.getlayer('IP')[0]
            innerPkt = frame.getlayer('IP')[1]
            assert innerPkt[IP].src == WEBSITE_REAL_IP
        elif DEFAULT_CHAIN_TYPE == CHAIN_TYPE_NSHOVERETH:
            condition = (frame[NSH].spi == self.spi \
                and frame[NSH].si == 0)
            if self.routeMorphic == IPV4_ROUTE_PROTOCOL:
                assert frame[NSH].nextproto == 0x1
                innerPkt = frame.getlayer('IP')[0]
                assert innerPkt[IP].src == WEBSITE_REAL_IP
            elif self.routeMorphic in [IPV6_ROUTE_PROTOCOL, SRV6_ROUTE_PROTOCOL]:
                assert frame[NSH].nextproto == 0x2
                innerPkt = frame.getlayer('IPv6')[0]
                assert innerPkt[IPv6].src == WEBSITE_REAL_IPV6
            elif self.routeMorphic == ROCEV1_ROUTE_PROTOCOL:
                assert frame[NSH].nextproto == 0x6
                # innerPkt = frame.getlayer('GRH')[0]
                # assert innerPkt[GRH].sgid == DGID
            else:
                raise ValueError("Unknown nextproto.")
        else:
            raise ValueError("Unknown chain type {0}".format(DEFAULT_CHAIN_TYPE))

    def verifyCmdRply(self, queueName, cmdID):
        cmdRply = self.recvCmdRply(queueName)
        assert cmdRply.cmdID == cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        assert cmdRply.attributes['zone'] == TURBONET_ZONE
        self.logger.info("Verify cmy rply successfully!")

    def verifyGetSFCIStateCmdRply(self, listenIP, listenPort, cmdID):
        cmdRply = self.recvCmdRplyByRPC(listenIP, listenPort)
        assert cmdRply.cmdID == cmdID
        assert cmdRply.cmdState == CMD_STATE_SUCCESSFUL
        assert cmdRply.attributes['zone'] == TURBONET_ZONE

        assert "sfcisDict" in cmdRply.attributes
        assert type(cmdRply.attributes["sfcisDict"]) == dict
        assert len(cmdRply.attributes["sfcisDict"]) >= 0
        sfcisDict = cmdRply.attributes["sfcisDict"]
        self.logger.info("get sfcisDict {0}".format(sfcisDict))
        for sfciID,sfci in sfcisDict.items():
            assert sfci.sfciID == sfciID
            assert len(sfci.vnfiSequence) != 0
            vnfiSequence = sfci.vnfiSequence
            for vnfis in vnfiSequence:
                for vnfi in vnfis:
                    vnfiStatus = vnfi.vnfiStatus
                    assert type(vnfiStatus) == VNFIStatus
                    if type(vnfi.node) == Server:
                        vnfType = vnfi.vnfType
                        if vnfType == VNF_TYPE_FW:
                            assert type(vnfiStatus.state) == ACLTable
                        elif vnfType == VNF_TYPE_MONITOR:
                            assert type(vnfiStatus.state) == MonitorStatistics
                            for directionID in [SFC_DIRECTION_0, SFC_DIRECTION_1]:
                                for routeProtocol in [IPV4_ROUTE_PROTOCOL, IPV6_ROUTE_PROTOCOL,
                                                        SRV6_ROUTE_PROTOCOL, ROCEV1_ROUTE_PROTOCOL]:
                                    self.logger.info("MonitorStatistics is {0}".format(
                                        vnfiStatus.state.getPktBytesRateStatisticDict(directionID, routeProtocol)))
                        elif vnfType == VNF_TYPE_RATELIMITER:
                            assert type(vnfiStatus.state) == RateLimiterConfig
                        else:
                            raise ValueError("Unknown vnf type {0}".format(vnfType))

        self.logger.info("Verify cmy rply successfully!")
