from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.ofproto import ofproto_v1_3_parser
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv4
from ryu.lib.packet import arp
from ryu.lib.packet import ether_types
from ryu.topology import event, switches 
from ryu.controller import dpset

import logging
import networkx as nx
import copy
from conf.ryuConf import *
from conf.genSwitchConf import SwitchConf
from sam.ryu.topoCollector import TopoCollector, TopologyChangeEvent
from sam.ryu.baseApp import BaseApp
from sam.base.messageAgent import *
from sam.base.command import *

DCNGATEWAY_INBOUND_PORT = 1
SWITCH_CLASSIFIER_PORT = 3

class UFFR(BaseApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {
        'dpset': dpset.DPSet,
        'TopoCollector': TopoCollector
        }

    def __init__(self, *args, **kwargs):
        super(UFFR, self).__init__(*args, **kwargs)
        self.dpset = kwargs['dpset']
        self.topoCollector = kwargs['TopoCollector']
        self.switch2Classifier = {} # {dpid:classifierMac}
        self._messageAgent = MessageAgent()
        self._messageAgent.startRecvMsg(NETWORK_CONTROLLER_QUEUE)
        self._commandsInfo = {}  # store all ryu commands
        self.logger.setLevel(logging.DEBUG)

        while True:
            msg = self._messageAgent.getMsg(NETWORK_CONTROLLER_QUEUE)
            if msg.getMessageType() == MSG_TYPE_NETWORK_CONTROLLER_CMD:
                logging.info("Ryu controller get a ryu cmd.")
                try:
                    cmd = msg.getbody()
                    self._commandsInfo[cmd.cmdID] = {"cmd":cmd,"state":CMD_STATE_PROCESSING}
                    if cmd.cmdType == CMD_TYPE_ADD_SFCI:
                        pass
                    elif cmd.cmdType == CMD_TYPE_DEL_SFCI:
                        pass
                    elif cmd.cmdType == CMD_TYPE_GET_TOPOLOGY:
                        pass
                    else:
                        logging.error("Unkonwn cmd type.")
                    self._commandsInfo[cmd.cmdID]["state"] = CMD_STATE_SUCCESSFUL
                except ValueError as err:
                    logging.error('ryu cmd processing error: ' + repr(err))
                    self._commandsInfo[cmd.cmdID]["state"] = CMD_STATE_FAIL
                finally:
                    rplyMsg = SAMMessage(MSG_TYPE_NETWORK_CONTROLLER_CMD_REPLY, CommandReply(cmd.cmdID,self._commandsInfo[cmd.cmdID]["state"]) )
                    if cmd.cmdType == CMD_TYPE_GET_TOPOLOGY:
                        queue = MEASUREMENT_QUEUE
                    else:
                        queue = ORCHESTRATION_QUEUE
                    self._messageAgent.sendMsg(queue,rplyMsg)
            elif msg.getMessageType() == None:
                pass
            else:
                logging.error("Unknown msg type.")

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id

        # install table-miss flow entry in UFFR_TABLE
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        self._add_flow(datapath, match, inst, table_id = UFFR_TABLE, priority=0)

        # initial CLASSIFIER_TABLE
        match = parser.OFPMatch(
            eth_type=ether_types.ETH_TYPE_IP,ipv4_dst="10.0.0.0/8"
        )
        inst = [parser.OFPInstructionGotoTable(table_id = UFFR_TABLE)]
        self._add_flow(datapath, match, inst, table_id = CLASSIFIER_TABLE, priority=2)

    def _setSwitch2Classifier(self, inPortNum, datapath, classifierMAC):
        dpid = datapath.id
        match = parser.OFPMatch(
            in_port=inPortNum, eth_type=ether_types.ETH_TYPE_IP
        )
        in_port_info = self.dpset.get_port(dpid, inPortNum)
        actions = [
            parser.OFPActionDecNwTtl(),
            parser.OFPActionSetField(eth_src=in_port_info.hw_addr),
            parser.OFPActionSetField(eth_dst=classifierMAC)
        ]
        inst = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,actions),
            parser.OFPInstructionGotoTable(table_id=L2_TABLE)
        ]
        self._add_flow(datapath,match,inst,table_id=MAIN_TABLE, priority=2)

    # group table set dst port design:
    # uffr.py use event to request mac-port mapping from _switchesLANMacTable in L2.py.
    # in L2.py, check _switchesLANMacTable, if it unexisted, return None, and send arp request.
    # if uffr get None, time.sleep(0.1) then retry again