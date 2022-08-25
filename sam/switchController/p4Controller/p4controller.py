import sam
import uuid

from agent.p4Agent import P4Agent
from agent.p4MonitorStatus import P4MonitorStat, P4MonitorEntry, P4MonitorStatus

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
from sam.base.sfc import SFC_DIRECTION_0, SFC_DIRECTION_1

P4CONTROLLER_P4_SWITCH_ID_1 = 20
P4CONTROLLER_P4_SWITCH_ID_2 = 21
DIRECTION_MASK_0 = 8388607
DIRECTION_MASK_1 = 8388608

class P4Controller:
    def __init__(self, _zonename):
        # message init
        logConf = LoggerConfigurator(__name__, './log', 'p4Controller.log', level='debug')
        self.logger = logConf.getLogger()
        self.logger.info('Initialize P4 controller.')
        self.zonename = _zonename
        self._messageAgent = MessageAgent()
        self.queueName = self._messageAgent.genQueueName(P4CONTROLLER_QUEUE, _zonename)
        self._messageAgent.startRecvMsg(self.queueName)
        # controller init
        self._commands = {}
        self._commandresults = {}
        self._sfclist = {}
        self._p4agent = {}
        self._p4monitor = {}
        # self._p4agent[0] = P4Agent('192.168.100.4:50052')
        # self._p4agent[1] = P4Agent('192.168.100.6:50052')
        self.logger.info('P4 controller initialization complete.')

    def getmsk(self, _addrstr):
        addr = ''
        msk = ''
        return addr, msk

    def run(self):
        while True:
            msg = self._messageAgent.getMsg(self.queueName)
            msgType = msg.getMessageType()
            if msgType == None:
                # get from grpc
                # get from digest
                pass
            elif msgType == MSG_TYPE_P4CONTROLLER_CMD:
                self.logger.info('Got a command.')
                cmd = msg.getbody()
                print(msg)
                self._commands[cmd.cmdID] = cmd
                self._commandresults[cmd.cmdID] = CMD_STATE_PROCESSING
                resdict = {}
                success = True
                if cmd.cmdType == CMD_TYPE_ADD_SFC:
                    success = True
                elif cmd.cmdType == CMD_TYPE_DEL_SFC:
                    success = True
                '''
                elif cmd.cmdType == CMD_TYPE_ADD_SFCI:
                    success1 = self._addsfc(cmd)
                    success2 = self._addsfci(cmd)
                    success = success1 & success2
                elif cmd.cmdType == CMD_TYPE_DEL_SFCI:
                    success1 = self._delsfc(cmd)
                    success2 = self._delsfci(cmd)
                    success = success1 & success2
                elif cmd.cmdType == CMD_TYPE_GET_SFCI_STATE:
                    success, resdict = self._getstate(cmd)
                else:
                    self.logger.error("Unsupported cmd type for P4 controller: %s." % cmd.cmdType)
                '''
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
    
    def _addsfc(self, _cmd):
        # send turbonet command
        sfc = _cmd.attributes['sfc']
        directions = sfc.directions
        sfci = _cmd.attributes['sfci']
        sfciID = sfci.sfciID
        for diri in directions:
            direthertype = ETH_TYPE_IPV4
            ignode = 0
            egnode = 0
            ignextnode = 0
            egnextnode = 0
            matchaddr = 0xF0FFFFFF
            dirspi = 0xFF0
            dirsi = 0xE
            dirnxtproto = 0x01
            # inbound
            p4M = P4Match(direthertype, src = None, dst = matchaddr)
            fVPList = [
                FieldValuePair(FIELD_TYPE_SPI, dirspi),
                FieldValuePair(FIELD_TYPE_SI, dirsi),
                FieldValuePair(FIELD_TYPE_NEXT_PROTOCOL, dirnxtproto),
                FieldValuePair(FIELD_TYPE_MDTYPE, 0x1)
            ]
            p4A = P4Action(actionType = ACTION_TYPE_ENCAPSULATION_NSH, nextNodeID = ignextnode, newFieldValueList = fVPList)
            p4CE = P4ClassifierEntry(nodeID = ignode, match = p4M, action = p4A)
            classifiercmd = Command(CMD_TYPE_ADD_CLASSIFIER_ENTRY, uuid.uuid1(), attributes = p4CE)
            classifiermsg = SAMMessage(MSG_TYPE_TURBONET_CONTROLLER_CMD, classifiercmd)
            self._messageAgent.sendMsgByRPC(TURBONET_CONTROLLER_IP, TURBONET_CONTROLLER_PORT, classifiermsg)
            # outbound
            p4M = P4Match(ETH_TYPE_NSH, src = matchaddr, dst = None)
            fVPList = [
                FieldValuePair(FIELD_TYPE_ETHERTYPE, direthertype)
            ]
            p4A = P4Action(actionType = ACTION_TYPE_DECAPSULATION_NSH, nextNodeID = egnextnode, newFieldValueList = fVPList)
            p4CE = P4ClassifierEntry(nodeID = egnode, match = p4M, action=p4A)
            classifiercmd = Command(CMD_TYPE_ADD_CLASSIFIER_ENTRY, uuid.uuid1(), attributes = p4CE)
            classifiermsg = SAMMessage(MSG_TYPE_TURBONET_CONTROLLER_CMD, classifiercmd)
            self._messageAgent.sendMsgByRPC(TURBONET_CONTROLLER_IP, TURBONET_CONTROLLER_PORT, classifiermsg)
        fpset = sfci.forwardingPathSet.primaryForwardingPath
        hasdir0 = False
        hasdir1 = False
        directions = _cmd.attributes['sfc'].directions
        if directions[0]['ID'] == SFC_DIRECTION_0:
            hasdir0 = True
        else:
            hasdir1 = True
        if len(directions) == 2:
            if directions[1]['ID'] == SFC_DIRECTION_0:
                hasdir0 = True
            else:
                hasdir1 = True
        if hasdir0:
            lst = fpset[DIRECTION0_PATHID_OFFSET]
            for segpath in lst:
                pathlen = len(segpath)
                for i in range(pathlen - 1):
                    fromnode = 0
                    tonode = 0
                    if fromnode == tonode:
                        continue
                    p4M = P4Match(ETH_TYPE_NSH, 0xF0FFFFFF)
                    p4A = P4Action(actionType = ACTION_TYPE_FORWARD, nextNodeID = tonode, newFieldValueList = None)
                    p4RE = P4RouteEntry(nodeID = fromnode, match = p4M, action = p4A)
                    routecmd = Command(CMD_TYPE_ADD_NSH_ROUTE, uuid.uuid1(), attributes = p4RE)
                    routemsg = SAMMessage(MSG_TYPE_TURBONET_CONTROLLER_CMD, routecmd)
                    self._messageAgent.sendMsgByRPC(TURBONET_CONTROLLER_IP, TURBONET_CONTROLLER_PORT, routemsg)
        if hasdir1:
            lst = fpset[DIRECTION1_PATHID_OFFSET]
            for segpath in lst:
                pathlen = len(segpath)
                for i in range(pathlen - 1):
                    fromnode = 0
                    tonode = 0
                    if fromnode == tonode:
                        continue
                    p4M = P4Match(ETH_TYPE_NSH, 0xF0FFFFFF)
                    p4A = P4Action(actionType = ACTION_TYPE_FORWARD, nextNodeID = tonode, newFieldValueList = None)
                    p4RE = P4RouteEntry(nodeID = fromnode, match = p4M, action = p4A)
                    routecmd = Command(CMD_TYPE_ADD_NSH_ROUTE, uuid.uuid1(), attributes = p4RE)
                    routemsg = SAMMessage(MSG_TYPE_TURBONET_CONTROLLER_CMD, routecmd)
                    self._messageAgent.sendMsgByRPC(TURBONET_CONTROLLER_IP, TURBONET_CONTROLLER_PORT, routemsg)
        return True
    
    def _addsfci(self, _cmd):
        sfci = _cmd.attributes['sfci']
        hasdir0 = False
        hasdir1 = False
        directions = _cmd.attributes['sfc'].directions
        if directions[0]['ID'] == SFC_DIRECTION_0:
            hasdir0 = True
        else:
            hasdir1 = True
        if len(directions) == 2:
            if directions[1]['ID'] == SFC_DIRECTION_0:
                hasdir0 = True
            else:
                hasdir1 = True
        sfciID = sfci.sfciID
        self.logger.info('Adding sfci %s.' % sfciID)
        nfseq = sfci.vnfiSequence
        si = len(nfseq)
        spi = sfciID
        routemorphic = sfci.routingMorphic.morphicName
        for nf in nfseq:
            eport = 136
            if si == 1:
                eport = 128
            for nfi in nf:
                if isinstance(nfi.node, Switch):
                    p4id = -1
                    if nfi.node.switchID == P4CONTROLLER_P4_SWITCH_ID_1:
                        p4id = 0
                    elif nfi.node.switchID == P4CONTROLLER_P4_SWITCH_ID_2:
                        p4id = 1
                    else:
                        continue
                    if nfi.vnfType == VNF_TYPE_FW:
                        if hasdir0:
                            self._p4agent[p4id].addIEGress(_service_path_index = (spi & DIRECTION_MASK_0), _service_index = si, _outport = eport)
                            fwlst = nfi.config.getRulesList(routemorphic)
                            for aclins in fwlst:
                                proto = aclins.proto
                                isdrop = (aclins.action == ACL_ACTION_DENY)
                                srcaddr, srcmsk = self.getmsk(aclins.srcAddr)
                                dstaddr, dstmsk = self.getmsk(aclins.dstAddr)
                                if routemorphic == IPV4_ROUTE_PROTOCOL:
                                    self._p4agent[p4id].addv4FWentry(
                                        _service_path_index = (spi & DIRECTION_MASK_0),
                                        _service_index = si,
                                        _src_addr = srcaddr,
                                        _dst_addr = dstaddr,
                                        _src_mask = srcmsk,
                                        _dst_mask = dstmsk,
                                        _nxt_hdr = proto,
                                        _priority = 0,
                                        _is_drop = isdrop
                                    )
                                else:
                                    self._p4agent[p4id].addv6FWentry(
                                        _service_path_index = (spi & DIRECTION_MASK_0),
                                        _service_index = si,
                                        _src_addr = srcaddr,
                                        _dst_addr = dstaddr,
                                        _src_mask = srcmsk,
                                        _dst_mask = dstmsk,
                                        _nxt_hdr = proto,
                                        _priority = 0,
                                        _is_drop = isdrop
                                    )
                        if hasdir1:
                            self._p4agent[p4id].addIEGress(_service_path_index = (spi | DIRECTION_MASK_1), _service_index = si, _outport = eport)
                            fwlst = nfi.config.getRulesList(routemorphic)
                            for aclins in fwlst:
                                proto = aclins.proto
                                isdrop = (aclins.action == ACL_ACTION_DENY)
                                srcaddr, srcmsk = self.getmsk(aclins.srcAddr)
                                dstaddr, dstmsk = self.getmsk(aclins.dstAddr)
                                if routemorphic == IPV4_ROUTE_PROTOCOL:
                                    self._p4agent[p4id].addv4FWentry(
                                        _service_path_index = (spi | DIRECTION_MASK_1),
                                        _service_index = si,
                                        _src_addr = srcaddr,
                                        _dst_addr = dstaddr,
                                        _src_mask = srcmsk,
                                        _dst_mask = dstmsk,
                                        _nxt_hdr = proto,
                                        _priority = 0,
                                        _is_drop = isdrop
                                    )
                                else:
                                    self._p4agent[p4id].addv6FWentry(
                                        _service_path_index = (spi | DIRECTION_MASK_1),
                                        _service_index = si,
                                        _src_addr = srcaddr,
                                        _dst_addr = dstaddr,
                                        _src_mask = srcmsk,
                                        _dst_mask = dstmsk,
                                        _nxt_hdr = proto,
                                        _priority = 0,
                                        _is_drop = isdrop
                                    )
                    elif nfi.vnfType == VNF_TYPE_RATELIMITER:
                        ratelim = nfi.config.maxMbps * 1024
                        if hasdir0:
                            self._p4agent[p4id].addIEGress(_service_path_index = (spi & DIRECTION_MASK_0), _service_index = si, _outport = eport)
                            self._p4agent[p4id].addRateLimiter(
                                _service_path_index = (spi & DIRECTION_MASK_0),
                                _service_index = si,
                                _cir = ratelim,
                                _cbs = ratelim,
                                _pir = ratelim,
                                _pbs = ratelim
                            )
                        if hasdir1:
                            self._p4agent[p4id].addIEGress(_service_path_index = (spi | DIRECTION_MASK_1), _service_index = si, _outport = eport)
                            self._p4agent[p4id].addRateLimiter(
                                _service_path_index = (spi | DIRECTION_MASK_1),
                                _service_index = si,
                                _cir = ratelim,
                                _cbs = ratelim,
                                _pir = ratelim,
                                _pbs = ratelim
                            )
                    elif nfi.vnfType == VNF_TYPE_MONITOR:
                        if hasdir0:
                            self._p4agent[p4id].addIEGress(_service_path_index = (spi & DIRECTION_MASK_0), _service_index = si, _outport = eport)
                            if routemorphic == IPV4_ROUTE_PROTOCOL:
                                self._p4agent[p4id].addMonitorv4(_service_path_index = (spi & DIRECTION_MASK_0), _service_index = si)
                            else:
                                self._p4agent[p4id].addMonitorv6(_service_path_index = (spi & DIRECTION_MASK_0), _service_index = si)
                        if hasdir1:
                            self._p4agent[p4id].addIEGress(_service_path_index = (spi | DIRECTION_MASK_1), _service_index = si, _outport = eport)
                            if routemorphic == IPV4_ROUTE_PROTOCOL:
                                self._p4agent[p4id].addMonitorv4(_service_path_index = (spi | DIRECTION_MASK_1), _service_index = si)
                            else:
                                self._p4agent[p4id].addMonitorv6(_service_path_index = (spi | DIRECTION_MASK_1), _service_index = si)
                    else:
                        return False
            si = si - 1
        return True
    
    def _getstate(self, _cmd):
        return True, {}
    
    def _delsfc(self, _cmd):
        # prepare to copy from add
        return True
    
    def _delsfci(self, _cmd):
        # prepare to copy from add
        return True
    
    def _updatemonitor(self, _p4id):
        pass
    
    def _addmonitorentry(self, _p4id, _service_path_index, _service_index, _src_addr, _dst_addr):
        pass

if __name__ == '__main__':
    p4ctl = P4Controller('')
    p4ctl.run()
