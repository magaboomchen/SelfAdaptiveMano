#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging

from sam.base.switch import *
from sam.base.server import *
from sam.base.link import *
from sam.test.testBase import *
from sam.orchestration.oSFCAdder import *
from sam.orchestration.oSFCDeleter import *
from sam.measurement.dcnInfoBaseMaintainer import *
from sam.base.loggerConfigurator import LoggerConfigurator

logging.basicConfig(level=logging.INFO)

DEFAULT_ZONE = ""


class TestOSFCAdderDeleterClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_collectDCNInfo(self):
        # setup
        logConfigur = LoggerConfigurator(__name__, level='info')
        self.logger = logConfigur.getLogger()

        self.sP = ShellProcessor()
        self.clearQueue()

        self.switches = {DEFAULT_ZONE:[]}
        self.switches[DEFAULT_ZONE].extend(
            self.genSwitchList(1, SWITCH_TYPE_DCNGATEWAY,
                ["2.2.0.32/27"], range(1,2))
        )
        self.switches[DEFAULT_ZONE].extend(
            self.genSwitchList(2, SWITCH_TYPE_TOR,
                ["2.2.0.64/27", "2.2.0.96/27"], range(2,4))
        )

        self.links = {DEFAULT_ZONE:[]}
        self.links[DEFAULT_ZONE] = [Link(1,2),Link(2,1),Link(1,3),
            Link(3,1),Link(2,3),Link(3,2)]

        self.servers = {DEFAULT_ZONE:[]}
        self.servers[DEFAULT_ZONE].extend(
            self.genServerList(1, SERVER_TYPE_CLASSIFIER,
            ["2.2.0.36"], ["2.2.0.35"], [SERVERID_OFFSET])
        )
        self.servers[DEFAULT_ZONE].extend(
            self.genServerList(1, SERVER_TYPE_NORMAL,
            ["2.2.0.34"], ["2.2.0.34"], [SERVERID_OFFSET+1])
        )
        self.servers[DEFAULT_ZONE].extend(
            self.genServerList(3, SERVER_TYPE_NFVI,
            ["2.2.0.69", "2.2.0.71", "2.2.0.99"],
            ["2.2.0.68", "2.2.0.70", "2.2.0.98"],
            range(SERVERID_OFFSET+2,SERVERID_OFFSET+2+3))
        )
        self.serverDict = {DEFAULT_ZONE:{}}
        for server in self.servers[DEFAULT_ZONE]:
            self.serverDict[DEFAULT_ZONE][server.getControlNICMac()] = {'Active': True,
            'timestamp': datetime.datetime(2020, 10, 27, 0, 2, 39, 408596),
            'server': server}
        self.logger.debug(self.serverDict)

        classifier = self.genClassifier("2.2.0.36")
        self.sfc = self.genUniDirectionSFC(classifier)
        self.sfci = SFCI(self._genSFCIID(), [],
            ForwardingPathSet=ForwardingPathSet({},"UFRR",{}))
        zoneName = self.sfc.attributes['zone']
        self.logger.info("zoneName:{0}".format(zoneName))
        self.addSFCRequest = self.genAddSFCRequest(self.sfc)
        self.addSFCIRequest = self.genAddSFCIRequest(self.sfc, self.sfci)
        self.delSFCIRequest = self.genDelSFCIRequest(self.sfc, self.sfci)
        self.delSFCRequest = self.genDelSFCRequest(self.sfc)

        self.oA = OSFCAdder(DCNInfoBaseMaintainer(), self.logger)
        self.oA._dib.updateServersInAllZone(self.serverDict)
        self.oA._dib.updateSwitchesInAllZone(self.switches)
        self.oA._dib.updateLinksInAllZone(self.links)

        self.oD = OSFCDeleter(DCNInfoBaseMaintainer(), self.logger)

        yield
        # teardown

    # @pytest.mark.skip(reason='Temporarly')
    def test_genAddSFCCmd(self, setup_collectDCNInfo):
        # exercise
        cmd = self.oA.genAddSFCCmd(self.addSFCRequest)
        sfc = cmd.attributes['sfc']
        self.logger.info(sfc)

        # verify
        assert sfc.sfcUUID == self.sfc.sfcUUID

    # @pytest.mark.skip(reason='Temporarly')
    def test_genAddSFCICmd(self, setup_collectDCNInfo):
        # exercise
        cmd = self.oA.genAddSFCICmd(self.addSFCIRequest)
        sfci = cmd.attributes['sfci']
        ForwardingPathSet = sfci.ForwardingPathSet
        primaryForwardingPath = ForwardingPathSet.primaryForwardingPath
        backupForwardingPath = ForwardingPathSet.backupForwardingPath

        # verify
        assert primaryForwardingPath == {1: [[10001, 1, 2, 10003], [10003, 2, 1, 10001]]}
        assert backupForwardingPath == {1: {(1, 2, 2): [[1, 3, 10005], [10005, 3, 1, 10001]], (2, 10003, 3): [[2, 10004], [10004, 2, 1, 10001]]}}

    # @pytest.mark.skip(reason='Temporarly')
    def test_genDelSFCICmd(self, setup_collectDCNInfo):
        # exercise
        cmd = self.oD.genDelSFCICmd(self.delSFCIRequest)
        sfc = cmd.attributes['sfc']
        sfci = cmd.attributes['sfci']

        # verify
        assert sfc.sfcUUID == self.sfc.sfcUUID
        assert sfci.SFCIID == self.sfci.SFCIID

    # @pytest.mark.skip(reason='Temporarly')
    def test_genDelSFCCmd(self, setup_collectDCNInfo):
        # exercise
        cmd = self.oD.genDelSFCCmd(self.delSFCRequest)
        sfc = cmd.attributes['sfc']

        # verify
        assert sfc.sfcUUID == self.sfc.sfcUUID


