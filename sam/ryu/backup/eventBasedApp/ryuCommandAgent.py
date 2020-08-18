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

from sam.ryu.conf.ryuConf import *
from sam.ryu.conf.genSwitchConf import SwitchConf
from sam.ryu.baseApp import BaseApp
from sam.base.messageAgent import *
from sam.base.command import *

import logging
import networkx as nx
import copy
from ryu.lib import hub

DCNGATEWAY_INBOUND_PORT = 1
SWITCH_CLASSIFIER_PORT = 3

class AddSfciEvent(event.EventBase):
    def __init__(self, msg):
        super(AddSfciEvent, self).__init__()
        self.msg = msg

class DelSfciEvent(event.EventBase):
    def __init__(self, msg):
        super(DelSfciEvent, self).__init__()
        self.msg = msg

class GetTopologyEvent(event.EventBase):
    def __init__(self, msg):
        super(GetTopologyEvent, self).__init__()
        self.msg = msg

# class CmdRplyEvent(event.EventBase):
#     def __init__(self, msg):
#         super(CmdRplyEvent, self).__init__()
#         self.msg = msg

class RyuCommandAgent(BaseApp):
    _EVENTS = [AddSfciEvent,DelSfciEvent,GetTopologyEvent]

    def __init__(self, *args, **kwargs):
        super(RyuCommandAgent, self).__init__(*args, **kwargs)
        self._messageAgent = MessageAgent()
        self._messageAgent.startRecvMsg(NETWORK_CONTROLLER_QUEUE)
        self.logger.setLevel(logging.DEBUG)

    def start(self):
        super(RyuCommandAgent, self).start()
        # Start user defined event loop
        self.threads.append(hub.spawn(self.startRyuCommandAgent))

    def startRyuCommandAgent(self):
        while True:
            hub.sleep(0.01)
            msg = self._messageAgent.getMsg(NETWORK_CONTROLLER_QUEUE)
            if msg.getMessageType() == MSG_TYPE_NETWORK_CONTROLLER_CMD:
                logging.info("Ryu command agent gets a ryu cmd.")
                cmd = msg.getbody()
                if cmd.cmdType == CMD_TYPE_ADD_SFCI:
                    print("Add sfci")
                    ev = AddSfciEvent(cmd)
                    self.send_event_to_observers(ev)
                    print("Send Add sfci event")
                elif cmd.cmdType == CMD_TYPE_DEL_SFCI:
                    ev = DelSfciEvent(cmd)
                    self.send_event_to_observers(ev)
                elif cmd.cmdType == CMD_TYPE_GET_TOPOLOGY:
                    ev = GetTopologyEvent(cmd)
                    self.send_event_to_observers(ev)
                else:
                    logging.error("Unkonwn cmd type.")
            elif msg.getMessageType() == None:
                pass
            else:
                logging.error("Unknown msg type.")

    # @set_ev_cls(CmdRplyEvent)
    # def _cmdReplyHandler(self, ev):
    #     print("RyuCommandAgent get a cmdRply !")
    #     cmdRply = ev.msg
    #     rplyMsg = SAMMessage(MSG_TYPE_NETWORK_CONTROLLER_CMD_REPLY,cmdRply)
    #     queue = MEASUREMENT_QUEUE
    #     self._messageAgent.sendMsg(queue,rplyMsg)

    def _cmdReplyHandler(self, cmdRply):
        print("RyuCommandAgent get a cmdRply !")
        rplyMsg = SAMMessage(MSG_TYPE_NETWORK_CONTROLLER_CMD_REPLY,cmdRply)
        queue = MEASUREMENT_QUEUE
        self._messageAgent.sendMsg(queue,rplyMsg)