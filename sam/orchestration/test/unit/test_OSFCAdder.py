#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging

from sam.base.switch import *
from sam.base.server import *
from sam.base.link import *
from sam.test.testBase import *
from sam.orchestration.oSFCAdder import *
from sam.measurement.dcnInfoBaseMaintainer import *

logging.basicConfig(level=logging.INFO)


class TestOSFCAdderClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_collectDCNInfo(self):
        # setup
        logConfigur = LoggerConfigurator(__name__, level='debug')
        self.logger = logConfigur.getLogger()

        self.sP = ShellProcessor()
        self.clearQueue()

        self.switches = {"":[]}
        self.switches[""].extend(
            self.genSwitchList(1, SWITCH_TYPE_DCNGATEWAY,
                ["2.2.0.32/27"], range(1,2))
        )
        self.switches[""].extend(
            self.genSwitchList(2, SWITCH_TYPE_TOR,
                ["2.2.0.64/27", "2.2.0.96/27"], range(2,4))
        )

        self.links = {"":[]}
        self.links[""] = [Link(1,2),Link(2,1),Link(1,3),
            Link(3,1),Link(2,3),Link(3,2)]

        self.servers = {"":[]}
        self.servers[""].extend(
            self.genServerList(1, SERVER_TYPE_CLASSIFIER,
            ["2.2.0.36"], ["2.2.0.35"], [SERVERID_OFFSET])
        )
        self.servers[""].extend(
            self.genServerList(1, SERVER_TYPE_NORMAL,
            ["2.2.0.34"], ["2.2.0.34"], [SERVERID_OFFSET+1])
        )
        self.servers[""].extend(
            self.genServerList(3, SERVER_TYPE_NFVI,
            ["2.2.0.69", "2.2.0.71", "2.2.0.99"],
            ["2.2.0.68", "2.2.0.70", "2.2.0.98"],
            range(SERVERID_OFFSET+2,SERVERID_OFFSET+2+3))
        )
        self.serverDict = {"":{}}
        for server in self.servers[""]:
            self.serverDict[""][server.getControlNICMac()] = {'Active': True,
            'timestamp': datetime.datetime(2020, 10, 27, 0, 2, 39, 408596),
            'server': server}
        self.logger.debug(self.serverDict)

        classifier = self.genClassifier("2.2.0.36")
        sfc = self.genUniDirectionSFC(classifier)
        zoneName = sfc.attributes['zone']
        self.request = self.genAddSFCIRequest(sfc)



        self.oA = OSFCAdder(DCNInfoBaseMaintainer(), self.logger)
        self.oA._dib.updateServersInAllZone(self.serverDict)
        self.oA._dib.updateSwitchesInAllZone(self.switches)
        self.oA._dib.updateLinksInAllZone(self.links)


        yield
        # teardown

    # @pytest.mark.skip(reason='Temporarly')
    def test_genAddSFCICmd(self, setup_collectDCNInfo):
        # exercise
        cmd = self.oA.genAddSFCICmd(self.request)
        sfci = cmd.attributes['sfci']
        ForwardingPathSet = sfci.ForwardingPathSet
        primaryForwardingPath = ForwardingPathSet.primaryForwardingPath
        backupForwardingPath = ForwardingPathSet.backupForwardingPath

        # verify
        assert primaryForwardingPath == {1: [[10001, 1, 2, 10003], [10003, 2, 1, 10001]]}
        assert backupForwardingPath == {1: {(1, 2, 2): [[1, 3, 10005], [10005, 3, 1, 10001]], (2, 10003, 3): [[2, 10004], [10004, 2, 1, 10001]]}}

