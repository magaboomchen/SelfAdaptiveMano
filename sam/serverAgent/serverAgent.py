#!/usr/bin/python
# -*- coding: UTF-8 -*-

import time

from sam.base.messageAgentAuxillary.msgAgentRPCConf import SERVER_AGENT_IP, \
                    SERVER_AGENT_PORT, SERVER_MANAGER_IP, SERVER_MANAGER_PORT
from sam.serverAgent.argParser import ArgParser
from sam.serverAgent.systemChecker import SystemChecker
from sam.serverAgent.bessStarter import BessStarter
from sam.serverAgent.dockerConfigurator import DockerConfigurator
from sam.serverAgent.dpdkConfigurator import DPDKConfigurator
from sam.base.server import Server
from sam.base.messageAgent import SAMMessage, MessageAgent, \
                                    MSG_TYPE_SERVER_REPLY
from sam.base.loggerConfigurator import LoggerConfigurator

HEAT_BEAT_TIME = 10


class ServerAgent(object):
    def __init__(self,controlNICName,   # type: str
                    serverType,         # type: str
                    datapathNICIP,      # type: str
                    nicPCIAddress,      # type: str
                    serverID            # type: int
                    ):
        logConfigur = LoggerConfigurator(__name__, './log',
            'serverAgent.log', level='info')
        self.logger = logConfigur.getLogger()
        self.logger.info('Init ServerAgent')
        self._messageAgent = MessageAgent(self.logger)
        self._messageAgent.startMsgReceiverRPCServer(SERVER_AGENT_IP, SERVER_AGENT_PORT)

        SystemChecker()
        DockerConfigurator().configDockerListenPort()

        self._server = Server(controlNICName, datapathNICIP, serverType)
        self._server.setServerID(serverID)
        self._server.updateControlNICMAC()
        self._server.updateIfSet()
        self._server.updateControlNICIP()

        self.grpcUrl = self._server.getControlNICIP() + ":10514"
        self.bS = BessStarter(self.grpcUrl)
        self.bS.killBessd() # must kill bessd first
        DPDKConfigurator(nicPCIAddress)
        self._server.updateDataPathNICMAC() # Then we can guarantee huge page
        self.bS.startBESSD()

    def run(self):
        self.logger.info("start server Agent routine")
        while True:
            # send server info to server controller
            self._server.updateIfSet()
            self._server.updateResource()
            self.logger.info(self._server)
            self._sendServerInfo()
            time.sleep(HEAT_BEAT_TIME)

    def _sendServerInfo(self):
        msg = SAMMessage(MSG_TYPE_SERVER_REPLY, self._server)
        self.logger.debug(msg.getMessageID())
        # self._messageAgent.sendMsg(SERVER_MANAGER_QUEUE ,msg)
        self._messageAgent.sendMsgByRPC(SERVER_MANAGER_IP, SERVER_MANAGER_PORT, msg)


if __name__=="__main__":
    argParser = ArgParser()
    nicPCIAddress = argParser.getArgs()['nicPciAddress']   # example: 0000:00:08.0
    controllNICName = argParser.getArgs()['controllNicName']   # example: ens3
    serverType = argParser.getArgs()['serverType']   # example: nfvi, classifier
    datapathNICIP = argParser.getArgs()['datapathNicIP']   # example: 2.2.0.38
    serverID = argParser.getArgs()['serverID']   # example: 10001

    serverAgent = ServerAgent(controllNICName,
                                serverType,
                                datapathNICIP,
                                nicPCIAddress,
                                serverID)
    serverAgent.run()
