#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging

from ryu.base.app_manager import lookup_service_brick
from ryu.lib import hub

from sam.base.messageAgent import NETWORK_CONTROLLER_QUEUE, MSG_TYPE_NETWORK_CONTROLLER_CMD
from sam.base.command import CMD_TYPE_ADD_SFC, \
    CMD_TYPE_ADD_SFCI, CMD_TYPE_DEL_SFCI, CMD_TYPE_DEL_SFC, CMD_TYPE_GET_TOPOLOGY, \
    CMD_TYPE_HANDLE_SERVER_STATUS_CHANGE
from sam.ryu.conf.ryuConf import ZONE_NAME
from sam.ryu.baseApp import BaseApp

# DCNGATEWAY_INBOUND_PORT = 1
# SWITCH_CLASSIFIER_PORT = 3


class RyuCommandAgent(BaseApp):
    def __init__(self, *args, **kwargs):
        super(RyuCommandAgent, self).__init__(*args, **kwargs)
        self.zoneName = ZONE_NAME
        self.queueName = self._messageAgent.genQueueName(
            NETWORK_CONTROLLER_QUEUE, self.zoneName)
        self._messageAgent.startRecvMsg(self.queueName)

        self.ufrr = lookup_service_brick("UFRR")
        self.tC = lookup_service_brick('TopoCollector')
        self.logger.setLevel(logging.DEBUG)

    def start(self):
        super(RyuCommandAgent, self).start()
        # Start user defined event loop
        self.threads.append(hub.spawn(self.startRyuCommandAgent))

    def startRyuCommandAgent(self):
        while True:
            hub.sleep(0.01)
            if self.ufrr == None:
                self.ufrr = lookup_service_brick("UFRR")
            msg = self._messageAgent.getMsg(self.queueName)
            if msg.getMessageType() == MSG_TYPE_NETWORK_CONTROLLER_CMD:
                self.logger.info("Ryu command agent gets a ryu cmd.")
                cmd = msg.getbody()
                if cmd.cmdType == CMD_TYPE_ADD_SFC:
                    self.ufrr._addSFCHandler(cmd)
                elif cmd.cmdType == CMD_TYPE_ADD_SFCI:
                    self.ufrr._addSFCIHandler(cmd)
                elif cmd.cmdType == CMD_TYPE_DEL_SFCI:
                    self.ufrr._delSFCIHandler(cmd)
                elif cmd.cmdType == CMD_TYPE_DEL_SFC:
                    self.ufrr._delSFCHandler(cmd)
                elif cmd.cmdType == CMD_TYPE_GET_TOPOLOGY:
                    self.tC.get_topology_handler(cmd)
                elif cmd.cmdType == CMD_TYPE_HANDLE_SERVER_STATUS_CHANGE:
                    self.ufrr._serverStatusChangeHandler(cmd)
                else:
                    self.logger.error("Unkonwn cmd type:{0}".format(cmd.cmdType))
            elif msg.getMessageType() == None:
                pass
            else:
                self.logger.error("Unknown msg type.")

