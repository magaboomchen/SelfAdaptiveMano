#!/usr/bin/python
# -*- coding: UTF-8 -*-

from ryu.topology.switches import switch, link, host


class TestMeasurerClass(TestFRR):
    @pytest.fixture(scope="function")
    def setup_TenThousandsServerDCNInfo(self):
        # setup
        self.switches = self.genSwitches()
        self.links = self.genLinks()
        self.hosts = self.genHosts()
        # self.runMeasurer()
        yield
        # teardown
        # self.killMeasurer()

    def test_getServerSet(self, setup_TenThousandsServerDCNInfo):
        # exercise
        getServerCmdRply = self.genGetServerCmdRply()
        self.sendCmd(MEASURER_QUEUE, MSG_TYPE_MEDIATOR_CMD_REPLY, getServerCmdRply)

        # verify

    def test_getTopology(self, setup_TenThousandsServerDCNInfo):
        # exercise
        getTopologyCmdRply = self.genGetTopologyCmdRply()
        self.sendCmd(MEASURER_QUEUE, MSG_TYPE_MEDIATOR_CMD_REPLY, getTopologyCmdRply)

        # verify

