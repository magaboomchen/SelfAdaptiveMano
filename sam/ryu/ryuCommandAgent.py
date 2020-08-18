from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.controller import dpset
from ryu.controller import event
from ryu.ofproto import ofproto_v1_3
from ryu.ofproto import ofproto_v1_3_parser
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv4
from ryu.lib.packet import arp
from ryu.lib.packet import ether_types
from ryu.topology import switches 
from ryu.base.app_manager import *

from sam.ryu.conf.ryuConf import *
from sam.ryu.conf.genSwitchConf import SwitchConf
from sam.ryu.baseApp import BaseApp
from sam.base.messageAgent import *
from sam.base.command import *

from sam.ryu.uffr import *

import logging
import networkx as nx
import copy
from ryu.lib import hub

DCNGATEWAY_INBOUND_PORT = 1
SWITCH_CLASSIFIER_PORT = 3

class RyuCommandAgent(BaseApp):
    def __init__(self, *args, **kwargs):
        super(RyuCommandAgent, self).__init__(*args, **kwargs)
        self._messageAgent.startRecvMsg(NETWORK_CONTROLLER_QUEUE)
        self.uffr = lookup_service_brick("UFFR")
        self.tC = lookup_service_brick('TopoCollector')
        self.logger.setLevel(logging.DEBUG)

    def start(self):
        super(RyuCommandAgent, self).start()
        # Start user defined event loop
        self.threads.append(hub.spawn(self.startRyuCommandAgent))

    def startRyuCommandAgent(self):
        while True:
            hub.sleep(0.01)
            if self.uffr == None:
                self.uffr = lookup_service_brick("UFFR")
            msg = self._messageAgent.getMsg(NETWORK_CONTROLLER_QUEUE)
            if msg.getMessageType() == MSG_TYPE_NETWORK_CONTROLLER_CMD:
                logging.info("Ryu command agent gets a ryu cmd.")
                cmd = msg.getbody()
                if cmd.cmdType == CMD_TYPE_ADD_SFCI:
                    print("Add sfci")
                    self.uffr._addSfciHandler(cmd)
                elif cmd.cmdType == CMD_TYPE_DEL_SFCI:
                    pass
                elif cmd.cmdType == CMD_TYPE_GET_TOPOLOGY:
                    pass
                else:
                    logging.error("Unkonwn cmd type.")
            elif msg.getMessageType() == None:
                pass
            else:
                logging.error("Unknown msg type.")