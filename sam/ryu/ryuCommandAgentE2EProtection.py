#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging

from ryu.base.app_manager import lookup_service_brick
from ryu.lib import hub

from sam.base.messageAgent import NETWORK_CONTROLLER_QUEUE, MSG_TYPE_NETWORK_CONTROLLER_CMD
from sam.base.command import CMD_TYPE_HANDLE_SERVER_STATUS_CHANGE, CMD_TYPE_ADD_SFC, \
    CMD_TYPE_ADD_SFCI, CMD_TYPE_DEL_SFCI, CMD_TYPE_DEL_SFC, \
    CMD_TYPE_GET_TOPOLOGY
from sam.ryu.conf.ryuConf import ZONE_NAME
from sam.ryu.baseApp import BaseApp


class RyuCommandAgent(BaseApp):
    def __init__(self, *args, **kwargs):
        super(RyuCommandAgent, self).__init__(*args, **kwargs)
        self.zoneName = ZONE_NAME
        self.queueName = self._messageAgent.genQueueName(
            NETWORK_CONTROLLER_QUEUE, self.zoneName)
        self._messageAgent.startRecvMsg(self.queueName)

        self.e2eProtection = lookup_service_brick("E2EProtection")
        self.tC = lookup_service_brick('TopoCollector')
        self.logger.setLevel(logging.WARNING)

    def start(self):
        super(RyuCommandAgent, self).start()
        # Start user defined event loop
        self.threads.append(hub.spawn(self.startRyuCommandAgent))

    def startRyuCommandAgent(self):
        while True:
            hub.sleep(0.01)
            if self.e2eProtection == None:
                self.e2eProtection = lookup_service_brick("E2EProtection")
            msg = self._messageAgent.getMsg(self.queueName)
            if msg.getMessageType() == MSG_TYPE_NETWORK_CONTROLLER_CMD:
                self.logger.info("Ryu command agent gets a ryu cmd.")
                cmd = msg.getbody()
                if cmd.cmdType == CMD_TYPE_ADD_SFC:
                    self.e2eProtection._addSFCHandler(cmd)
                elif cmd.cmdType == CMD_TYPE_ADD_SFCI:
                    self.e2eProtection._addSFCIHandler(cmd)
                elif cmd.cmdType == CMD_TYPE_DEL_SFCI:
                    self.e2eProtection._delSFCIHandler(cmd)
                elif cmd.cmdType == CMD_TYPE_DEL_SFC:
                    self.e2eProtection._delSFCHandler(cmd)
                elif cmd.cmdType == CMD_TYPE_GET_TOPOLOGY:
                    self.tC.get_topology_handler(cmd)
                elif cmd.cmdType == CMD_TYPE_HANDLE_SERVER_STATUS_CHANGE:
                    self.e2eProtection._serverStatusChangeHandler(cmd)
                else:
                    self.logger.error("Unkonwn cmd type:{0}".format(cmd.cmdType))
            elif msg.getMessageType() == None:
                pass
            else:
                self.logger.error("Unknown msg type.")

