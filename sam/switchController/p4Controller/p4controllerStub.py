import sam
import uuid
from sam.base.command import CMD_TYPE_GET_SFCI_STATE, CommandReply, CMD_TYPE_ADD_SFC, CMD_TYPE_DEL_SFC, CMD_TYPE_ADD_SFCI, CMD_TYPE_DEL_SFCI, CMD_STATE_SUCCESSFUL, CMD_STATE_FAIL, CMD_STATE_PROCESSING
from sam.base.command import CMD_TYPE_DEL_CLASSIFIER_ENTRY, CMD_TYPE_DEL_NSH_ROUTE, Command, CMD_TYPE_ADD_NSH_ROUTE, CMD_TYPE_ADD_CLASSIFIER_ENTRY
from sam.base.server import Server
from sam.base.switch import Switch
from sam.base.messageAgent import SAMMessage, MessageAgent, P4CONTROLLER_QUEUE, MSG_TYPE_P4CONTROLLER_CMD, MSG_TYPE_P4CONTROLLER_CMD_REPLY, MEDIATOR_QUEUE, TURBONET_ZONE
from sam.base.messageAgent import MSG_TYPE_TURBONET_CONTROLLER_CMD
from sam.base.messageAgentAuxillary.msgAgentRPCConf import TEST_PORT, TURBONET_CONTROLLER_IP, TURBONET_CONTROLLER_PORT, P4_CONTROLLER_PORT, P4_CONTROLLER_IP
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.vnf import VNFIStatus
from sam.base.routingMorphic import IPV4_ROUTE_PROTOCOL, IPV6_ROUTE_PROTOCOL, ROCEV1_ROUTE_PROTOCOL, SRV6_ROUTE_PROTOCOL
from sam.base.vnf import VNF_TYPE_FORWARD, VNF_TYPE_FW, VNF_TYPE_MONITOR, VNF_TYPE_LB, VNF_TYPE_NAT, VNF_TYPE_RATELIMITER, VNF_TYPE_VPN
from sam.base.acl import ACLTable, ACLTuple, ACL_ACTION_ALLOW, ACL_ACTION_DENY, ACL_PROTO_TCP, ACL_PROTO_ICMP, ACL_PROTO_IGMP, ACL_PROTO_IPIP, ACL_PROTO_UDP
from sam.base.path import DIRECTION0_PATHID_OFFSET, DIRECTION1_PATHID_OFFSET, MAPPING_TYPE_MMLPSFC, ForwardingPathSet
from sam.base.rateLimiter import RateLimiterConfig
from sam.switchController.base.p4ClassifierEntry import P4ClassifierEntry
from sam.switchController.base.p4Action import ACTION_TYPE_DECAPSULATION_NSH, ACTION_TYPE_ENCAPSULATION_NSH, ACTION_TYPE_FORWARD, FIELD_TYPE_ETHERTYPE, FIELD_TYPE_MDTYPE, FIELD_TYPE_NEXT_PROTOCOL, FIELD_TYPE_SI, FIELD_TYPE_SPI, P4Action, FieldValuePair
from sam.switchController.base.p4Match import ETH_TYPE_IPV4, ETH_TYPE_NSH, P4Match, ETH_TYPE_IPV6, ETH_TYPE_ROCEV1
from sam.switchController.base.p4RouteEntry import P4RouteEntry

P4CONTROLLER_P4_SWITCH_ID_1 = 20
P4CONTROLLER_P4_SWITCH_ID_2 = 21
DIRECTION_MASK_0 = 8388607
DIRECTION_MASK_1 = 8388608

class P4Controller:
    def __init__(self, _zonename):
        logConf = LoggerConfigurator(__name__, './log', 'p4Controller.log', level='debug')
        self.logger = logConf.getLogger()
        self.logger.info('Initialize P4 controller.')
        self.zonename = _zonename
        self._messageAgent = MessageAgent()
        self.queueName = self._messageAgent.genQueueName(P4CONTROLLER_QUEUE, _zonename)
        self._messageAgent.startRecvMsg(self.queueName)
        self._commands = {}
        self._commandresults = {}
        self._sfclist = {}
        self.logger.info('P4 controller initialization complete.')

    def run(self):
        while True:
            msg = self._messageAgent.getMsg(self.queueName)
            msgType = msg.getMessageType()
            if msgType == None:
                msg = self._messageAgent.getMsgByRPC(P4_CONTROLLER_IP, P4_CONTROLLER_PORT)
                msgType = msg.getMessageType()
                if msgType == None:
                    pass
                elif msgType == MSG_TYPE_P4CONTROLLER_CMD:
                    self.logger.info('Got a command from rpc')
                    cmd = msg.getbody()
                    self._commands[cmd.cmdID] = cmd
                    self._commandresults[cmd.cmdID] = CMD_STATE_PROCESSING
                    resdict = {}
                    success = True
                    if success:
                        self._commandresults[cmd.cmdID] = CMD_STATE_SUCCESSFUL
                    else:
                        self._commandresults[cmd.cmdID] = CMD_STATE_FAIL
                    cmdreply = CommandReply(cmd.cmdID, self._commandresults[cmd.cmdID])
                    cmdreply.attributes["zone"] = TURBONET_ZONE
                    cmdreply.attributes.update(resdict)
                    replymessage = SAMMessage(MSG_TYPE_P4CONTROLLER_CMD_REPLY, cmdreply)
                    self._messageAgent.sendMsgByRPC(P4_CONTROLLER_IP, P4_CONTROLLER_PORT, replymessage)
            elif msgType == MSG_TYPE_P4CONTROLLER_CMD:
                self.logger.info('Got a command.')
                cmd = msg.getbody()
                self._commands[cmd.cmdID] = cmd
                self._commandresults[cmd.cmdID] = CMD_STATE_PROCESSING
                resdict = {}
                success = True
                if success:
                    self._commandresults[cmd.cmdID] = CMD_STATE_SUCCESSFUL
                else:
                    self._commandresults[cmd.cmdID] = CMD_STATE_FAIL
                cmdreply = CommandReply(cmd.cmdID, self._commandresults[cmd.cmdID])
                cmdreply.attributes["zone"] = TURBONET_ZONE
                cmdreply.attributes.update(resdict)
                replymessage = SAMMessage(MSG_TYPE_P4CONTROLLER_CMD_REPLY, cmdreply)
                self._messageAgent.sendMsg(MEDIATOR_QUEUE, replymessage)
            else:
                self.logger.error('Unsupported msg type for P4 controller: %s.' % msg.getMessageType())

if __name__ == '__main__':
    p4ctl = P4Controller('')
    p4ctl.run()
