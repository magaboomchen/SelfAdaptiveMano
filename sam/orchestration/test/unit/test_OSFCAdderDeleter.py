#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging
import sys
if sys.version > '3':
    import queue as Queue
else:
    import Queue

from sam.base.path import *
from sam.base.switch import *
from sam.base.server import *
from sam.base.link import Link, LINK_DEFAULT_BANDWIDTH
from sam.test.testBase import *
from sam.orchestration.oSFCAdder import *
from sam.orchestration.oSFCDeleter import *
from sam.measurement.dcnInfoBaseMaintainer import *
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer

# logging.basicConfig(level=logging.WARNING)

DEFAULT_ZONE = ""

MODE_UFRR = 0
MODE_NOTVIA_REMAPPING = 1
MODE_NOTVIA_PSFC = 2
MODE_END2END_PROTECTION = 3
MODE_DIRECT_REMAPPING = 4


class TestOSFCAdderDeleterClass(TestBase):
    @classmethod
    def setup_class(cls):
        cls.tc = TestOSFCAdderDeleterClass()

        # setup
        logConfigur = LoggerConfigurator(__name__, level='info')
        cls.logger = logConfigur.getLogger()

        cls.sP = ShellProcessor()
        cls.tc.clearQueue()

        cls._genSwitchDict()
        cls._genLinkDict()
        cls._genServerDict()

        classifier = cls.tc.genClassifier("2.2.0.36")
        cls.sfc = cls.tc.genUniDirectionSFC(classifier)
        cls.sfc.slo = SLO(latencyBound=10, throughput=0.005)
        cls.sfci = SFCI(cls.tc._genSFCIID(), [],
            forwardingPathSet=ForwardingPathSet({}, MAPPING_TYPE_NOTVIA_PSFC, {}))
        zoneName = cls.sfc.attributes['zone']
        cls.logger.info("zoneName:{0}".format(zoneName))
        cls.addSFCRequest = cls.tc.genAddSFCRequest(cls.sfc)
        cls.addSFCIRequest = cls.tc.genAddSFCIRequest(cls.sfc, cls.sfci)
        cls.delSFCIRequest = cls.tc.genDelSFCIRequest(cls.sfc, cls.sfci)
        cls.delSFCRequest = cls.tc.genDelSFCRequest(cls.sfc)

        cls._dib = DCNInfoBaseMaintainer()
        cls._oib = OrchInfoBaseMaintainer("localhost", "dbAgent", "123")

        cls.oA = OSFCAdder(cls._dib, cls.logger)
        cls.oA._dib.updateServersInAllZone(cls.servers)
        cls.oA._dib.updateSwitchesInAllZone(cls.switches)
        cls.oA._dib.updateLinksInAllZone(cls.links)

        cls.oD = OSFCDeleter(cls._dib, cls._oib, cls.logger)

    @classmethod
    def teardown_class(cls):
        cls._oib.dbA.dropTable("Request")
        cls._oib.dbA.dropTable("SFC")
        cls._oib.dbA.dropTable("SFCI")

    @classmethod
    def _genSwitchDict(cls):
        cls.switches = {DEFAULT_ZONE:{}}

        switchList = cls.tc.genSwitchList(1, SWITCH_TYPE_DCNGATEWAY,
                ["2.2.0.32/27"], range(1,2))
        for switch in switchList:
            switchID = switch.switchID
            cls.switches[DEFAULT_ZONE][switchID] = {'switch':switch,
                'Active':True}

        switchList = cls.tc.genSwitchList(2, SWITCH_TYPE_NPOP,
                ["2.2.0.64/27", "2.2.0.96/27"], range(2,4), 
                supportVNFList=[range(VNF_TYPE_MAX+1), range(VNF_TYPE_MAX+1)])
        for switch in switchList:
            switchID = switch.switchID
            cls.switches[DEFAULT_ZONE][switchID] = {'switch': switch,
                'Active': True}

    @classmethod
    def _genLinkDict(cls):
        cls.links = {DEFAULT_ZONE:{}}
        cls.links[DEFAULT_ZONE] = {
            (1,2):{'link':Link(1,2),'Active':True},
            (2,1):{'link':Link(2,1),'Active':True},
            (1,3):{'link':Link(1,3),'Active':True},
            (3,1):{'link':Link(3,1),'Active':True},
            (2,3):{'link':Link(2,3),'Active':True},
            (3,2):{'link':Link(3,2),'Active':True},
            }

    @classmethod
    def _genServerDict(cls):
        serversDictList = {DEFAULT_ZONE:[]}
        serversDictList[DEFAULT_ZONE].extend(
            cls.tc.genServerList(1, SERVER_TYPE_CLASSIFIER,
            ["2.2.0.36"], ["2.2.0.35"], [SERVERID_OFFSET])
        )
        serversDictList[DEFAULT_ZONE].extend(
            cls.tc.genServerList(1, SERVER_TYPE_NORMAL,
            ["2.2.0.34"], ["2.2.0.34"], [SERVERID_OFFSET+1])
        )
        serversDictList[DEFAULT_ZONE].extend(
            cls.tc.genServerList(3, SERVER_TYPE_NFVI,
            ["2.2.0.69", "2.2.0.71", "2.2.0.99"],
            ["2.2.0.68", "2.2.0.70", "2.2.0.98"],
            range(SERVERID_OFFSET+2,SERVERID_OFFSET+2+3))
        )
        cls.servers = {DEFAULT_ZONE:{}}
        for server in serversDictList[DEFAULT_ZONE]:
            cls.servers[DEFAULT_ZONE][server.getServerID()] = {
                'Active': True,
                'timestamp': datetime.datetime(2020, 10, 27, 0, 2, 39, 408596),
                'server': server}
        cls.logger.debug("serverDict:{0}".format(cls.servers))

    @pytest.mark.skip(reason='Temporarly')
    def test_genAddSFCCmd(self):
        # exercise
        cmd = self.oA.genAddSFCCmd(self.addSFCRequest)
        self._oib.addSFCRequestHandler(self.addSFCRequest, cmd)
        sfc = cmd.attributes['sfc']
        self.logger.info(sfc)

        # verify
        assert sfc.sfcUUID == self.sfc.sfcUUID

    @pytest.mark.skip(reason='Temporarly')
    def test_genAddSFCICmd(self):
        # exercise
        cmd = self.oA.genAddSFCICmd(self.addSFCIRequest)
        self._oib.addSFCIRequestHandler(self.addSFCIRequest, cmd)

        sfci = cmd.attributes['sfci']
        forwardingPathSet = sfci.forwardingPathSet
        primaryForwardingPath = forwardingPathSet.primaryForwardingPath
        backupForwardingPath = forwardingPathSet.backupForwardingPath

        # verify
        assert primaryForwardingPath == {1: [[10001, 1, 2, 10003], [10003, 2, 1, 10001]]}
        assert backupForwardingPath == {1: {(1, 2, 2): [[1, 3, 10005], [10005, 3, 1, 10001]], (2, 10003, 3): [[2, 10004], [10004, 2, 1, 10001]]}}

    @pytest.mark.skip(reason='Temporarly')
    def test_genDelSFCICmd(self):
        # exercise
        cmd = self.oD.genDelSFCICmd(self.delSFCIRequest)
        self._oib.delSFCIRequestHandler(self.delSFCIRequest, cmd)
        sfc = cmd.attributes['sfc']
        sfci = cmd.attributes['sfci']

        # verify
        assert sfc.sfcUUID == self.sfc.sfcUUID
        assert sfci.sfciID == self.sfci.sfciID

    @pytest.mark.skip(reason='Temporarly')
    def test_genDelSFCCmd(self):
        # exercise
        cmd = self.oD.genDelSFCCmd(self.delSFCRequest)
        self._oib.delSFCRequestHandler(self.delSFCRequest, cmd)
        sfc = cmd.attributes['sfc']

        # verify
        assert sfc.sfcUUID == self.sfc.sfcUUID

    @pytest.mark.skip(reason='Temporarly')
    def test_genABatchOfRequestAndAddSFCICmdsReuseVNFI(self):
        # exercise
        self._requestBatchQueue = Queue.Queue()
        self.addSFCIRequest.attributes['mappingType'] = MAPPING_TYPE_UFRR
        self._requestBatchQueue.put(self.addSFCIRequest)
        self._requestBatchQueue.put(self.addSFCIRequest)

        requestCmdBatch = self.oA.genABatchOfRequestAndAddSFCICmds(
            self._requestBatchQueue)

        # verify
        for (request, cmd) in requestCmdBatch:
            sfci = cmd.attributes['sfci']
            self.logVNFISeq(sfci.vnfiSequence)
            forwardingPathSet = sfci.forwardingPathSet
            primaryForwardingPath = forwardingPathSet.primaryForwardingPath
            backupForwardingPath = forwardingPathSet.backupForwardingPath
            self.logger.info("forwardingPathSet:{0}".format(
                forwardingPathSet))
            raw_input()
            # each time will print (vnfiID, serverID) information
            # if program reuse vnfi, you will find that the same (vnfiID, serverID) twice

            assert True == True

    @pytest.mark.skip(reason='Temporarly')
    def test_genABatchOfRequestAndAddSFCICmdsUFRR(self):
        # exercise
        self._requestBatchQueue = Queue.Queue()
        self.addSFCIRequest.attributes['mappingType'] = MAPPING_TYPE_UFRR
        self._requestBatchQueue.put(self.addSFCIRequest)

        requestCmdBatch = self.oA.genABatchOfRequestAndAddSFCICmds(
            self._requestBatchQueue)

        # verify
        for (request, cmd) in requestCmdBatch:
            sfci = cmd.attributes['sfci']
            # self.logVNFISeq(sfci.vnfiSequence)
            forwardingPathSet = sfci.forwardingPathSet
            primaryForwardingPath = forwardingPathSet.primaryForwardingPath
            backupForwardingPath = forwardingPathSet.backupForwardingPath
            # self.logger.info("forwardingPathSet:{0}".format(
            #     forwardingPathSet))

            assert primaryForwardingPath == {1: [[(0, 10001), (0, 1), (0, 3), (0, 10005)], [(1, 10005), (1, 3), (1, 1), (1, 10001)]]}
            assert backupForwardingPath == {1: 
                    {(('failureNodeID', 3), ('repairMethod', 'fast-reroute'), ('repairSwitchID', 1), ('newPathID', 2)):
                            [[(0, 1), (0, 2), (0, 10003)], [(1, 10003), (1, 2), (1, 1), (1, 10001)]],
                        (('failureNodeID', 10005), ('repairMethod', 'fast-reroute'), ('repairSwitchID', 3), ('newPathID', 3)):
                            [[(0, 3), (0, 2), (0, 10003)], [(1, 10003), (1, 2), (1, 1), (1, 10001)]]}}

    @pytest.mark.skip(reason='Temporarly')
    def test_genABatchOfRequestAndAddSFCICmdsNotViaPSFC(self):
        # exercise
        self._requestBatchQueue = Queue.Queue()
        self.addSFCIRequest.attributes['mappingType'] = MAPPING_TYPE_NOTVIA_PSFC
        self._requestBatchQueue.put(self.addSFCIRequest)

        requestCmdBatch = self.oA.genABatchOfRequestAndAddSFCICmds(
            self._requestBatchQueue)

        # verify
        for (request, cmd) in requestCmdBatch:
            sfci = cmd.attributes['sfci']
            # self.logVNFISeq(sfci.vnfiSequence)
            forwardingPathSet = sfci.forwardingPathSet
            primaryForwardingPath = forwardingPathSet.primaryForwardingPath
            backupForwardingPath = forwardingPathSet.backupForwardingPath
            # self.logger.info("forwardingPathSet:{0}".format(
            #     forwardingPathSet))

            assert primaryForwardingPath != None
            assert backupForwardingPath != None

    # @pytest.mark.skip(reason='Temporarly')
    def test_genABatchOfRequestAndAddSFCICmdsDPSFC(self):
        # exercise
        self._requestBatchQueue = Queue.Queue()
        self.addSFCIRequest.attributes['mappingType'] = MAPPING_TYPE_E2EP
        self._requestBatchQueue.put(self.addSFCIRequest)

        requestCmdBatch = self.oA.genABatchOfRequestAndAddSFCICmds(
            self._requestBatchQueue)

        # verify
        for (request, cmd) in requestCmdBatch:
            sfci = cmd.attributes['sfci']
            # self.logVNFISeq(sfci.vnfiSequence)
            forwardingPathSet = sfci.forwardingPathSet
            primaryForwardingPath = forwardingPathSet.primaryForwardingPath
            backupForwardingPath = forwardingPathSet.backupForwardingPath
            # self.logger.info("forwardingPathSet:{0}".format(
            #     forwardingPathSet))

            assert primaryForwardingPath != None
            assert backupForwardingPath != None

    def logVNFISeq(self, vnfiSequence):
        self.logger.info("vnfiSequence")
        for stage in range(len(vnfiSequence)):
            vnfiList = vnfiSequence[stage]
            for vnfi in vnfiList:
                if type(vnfi.node) == Server:
                    self.logger.info(
                        "stage:{0}, vnfiID:{1} @ serverID:{2}".format(
                            stage, vnfi.vnfiID, vnfi.node.getServerID()))
                else:
                    raise ValueError(
                        "Unknown vnfi node type {0}".format(
                            type(vnfi.node)))
