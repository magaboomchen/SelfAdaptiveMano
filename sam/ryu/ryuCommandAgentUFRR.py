#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging

from ryu.controller import event
from ryu.base.app_manager import *
from ryu.lib import hub

from sam.base.messageAgent import *
from sam.base.command import *
from sam.ryu.conf.ryuConf import *
from sam.ryu.baseApp import BaseApp

DCNGATEWAY_INBOUND_PORT = 1
SWITCH_CLASSIFIER_PORT = 3


class RyuCommandAgent(BaseApp):
    def __init__(self, *args, **kwargs):
        super(RyuCommandAgent, self).__init__(*args, **kwargs)
        self._messageAgent.startRecvMsg(NETWORK_CONTROLLER_QUEUE)
        self.ufrr = lookup_service_brick("UFRR")
        self.notVia = lookup_service_brick("NotVia")
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
            if self.notVia == None:
                self.notVia = lookup_service_brick("NotVia")
            msg = self._messageAgent.getMsg(NETWORK_CONTROLLER_QUEUE)
            if msg.getMessageType() == MSG_TYPE_NETWORK_CONTROLLER_CMD:
                self.logger.info("Ryu command agent gets a ryu cmd.")
                cmd = msg.getbody()
                if cmd.cmdType == CMD_TYPE_ADD_SFC:
                    self.ufrr._addSfcHandler(cmd)
                elif cmd.cmdType == CMD_TYPE_ADD_SFCI:
                    self.ufrr._addSfciHandler(cmd)
                elif cmd.cmdType == CMD_TYPE_DEL_SFCI:
                    self.ufrr._delSfciHandler(cmd)
                elif cmd.cmdType == CMD_TYPE_DEL_SFC:
                    self.ufrr._delSfcHandler(cmd)
                elif cmd.cmdType == CMD_TYPE_GET_TOPOLOGY:
                    self.tC.get_topology_handler(cmd)
                else:
                    self.logger.error("Unkonwn cmd type:{0}".format(cmd.cmdType))
            elif msg.getMessageType() == None:
                pass
            else:
                self.logger.error("Unknown msg type.")

