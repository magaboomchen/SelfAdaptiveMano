#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid
import pytest
import logging

from sam.base.switch import Switch, SWITCH_TYPE_NPOP
from sam.base.server import Server, SERVER_TYPE_NORMAL
from sam.base.request import Request, REQUEST_STATE_SUCCESSFUL, \
    REQUEST_TYPE_GET_DCN_INFO
from sam.base.link import Link
from sam.base.messageAgent import DEFAULT_ZONE, MEDIATOR_QUEUE, MEASURER_QUEUE, \
    MSG_TYPE_MEDIATOR_CMD_REPLY, ORCHESTRATOR_QUEUE, DCN_INFO_RECIEVER_QUEUE
from sam.base.command import CommandReply, CMD_TYPE_GET_TOPOLOGY, CMD_STATE_SUCCESSFUL
from sam.base.shellProcessor import ShellProcessor
from sam.measurement import measurer
from sam.test.testBase import TestBase

logging.basicConfig(level=logging.INFO)


class TestMeasurerClass(TestBase):
    @pytest.fixture(scope="function")
    def setup_collectDCNInfo(self):
        # setup
        self.sP = ShellProcessor()
        self.clearQueue()

        self.runMeasurer()

        yield
        # teardown
        self.killMeasurer()

    @pytest.mark.skip(reason='Temporarly')
    def test_collectTopology(self, setup_collectDCNInfo):
        # exercise
        cmd = self.recvCmd(MEDIATOR_QUEUE)
        self.replyGetTopologyCmd(cmd)
        # verify
        assert cmd.cmdType == CMD_TYPE_GET_TOPOLOGY

    def replyGetTopologyCmd(self, cmd):
        if cmd.cmdType == CMD_TYPE_GET_TOPOLOGY:
            logging.info("Get topology command")
            self.attr = self.genTopoAttr()
            cmdRply = CommandReply(cmd.cmdID, CMD_STATE_SUCCESSFUL,
                attributes=self.attr)
            self.sendCmdRply(MEASURER_QUEUE, MSG_TYPE_MEDIATOR_CMD_REPLY, 
                cmdRply)

    def genTopoAttr(self):
        switchList = []
        switch = Switch(uuid.uuid1(), SWITCH_TYPE_NPOP)
        switchList.append(switch)

        linkList = []
        link = Link(1,2)
        linkList.append(link)

        return {'switches':switchList,
                'links':linkList,
                'zone':DEFAULT_ZONE
                }

    def genServerAttr(self):
        serverList = []
        server = Server("ens3", "2.2.0.34", SERVER_TYPE_NORMAL)
        serverList.append(server)

        return {'servers':serverList}

    def runMeasurer(self):
        filePath = measurer.__file__
        logging.error(filePath)
        self.sP.runPythonScript(filePath)

    def killMeasurer(self):
        self.sP.killPythonScript("/measurement/measurer.py")


    @pytest.fixture(scope="function")
    def setup_handleRequest(self):
        logging.info("setup_handleRequest")
        # setup
        self.sP = ShellProcessor()
        self.clearQueue()

        self.runMeasurer()

        cmd = self.recvCmd(MEDIATOR_QUEUE)
        self.replyGetTopologyCmd(cmd)

        yield
        # teardown
        self.killMeasurer()

    # @pytest.mark.skip(reason='Temporarly')
    def test_requestHandler(self, setup_handleRequest):
        logging.info("test_requestHanler")
        # exercise
        request = self.genGetDCNInfoRequest(ORCHESTRATOR_QUEUE)
        self.sendRequest(MEASURER_QUEUE, request)

        # verify
        reply = self.recvReply(DCN_INFO_RECIEVER_QUEUE)
        assert reply.requestID == request.requestID
        assert reply.requestState == REQUEST_STATE_SUCCESSFUL

        for key,values in reply.attributes.items():
            logging.info("{0},{1}".format(key, values))
            # if type(values) == list:
            #     for item in values:
            #         logging.info(item)

    def genGetDCNInfoRequest(self, srcQueue):
        request = Request(0, uuid.uuid1(), REQUEST_TYPE_GET_DCN_INFO,
            srcQueue)
        return request

