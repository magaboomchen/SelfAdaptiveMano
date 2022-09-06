import sam
import uuid
import time
import socket
import ipaddress
from binascii import hexlify

from agent.p4Agent import P4Agent
from agent.p4MonitorStatus import P4MonitorStat, P4MonitorEntry, P4MonitorStatus

from sam.base.command import CMD_TYPE_GET_SFCI_STATE, CommandReply, CMD_TYPE_ADD_SFC, CMD_TYPE_DEL_SFC, CMD_TYPE_ADD_SFCI, CMD_TYPE_DEL_SFCI, CMD_STATE_SUCCESSFUL, CMD_STATE_FAIL, CMD_STATE_PROCESSING
from sam.base.command import CMD_TYPE_DEL_CLASSIFIER_ENTRY, CMD_TYPE_DEL_NSH_ROUTE, Command, CMD_TYPE_ADD_NSH_ROUTE, CMD_TYPE_ADD_CLASSIFIER_ENTRY
from sam.base.server import Server
from sam.base.switch import Switch
from sam.base.sfc import SFCI
from sam.base.messageAgent import SAMMessage, MessageAgent, P4CONTROLLER_QUEUE, MSG_TYPE_P4CONTROLLER_CMD, MSG_TYPE_P4CONTROLLER_CMD_REPLY, MEDIATOR_QUEUE, TURBONET_ZONE
from sam.base.messageAgent import MSG_TYPE_TURBONET_CONTROLLER_CMD
from sam.base.messageAgentAuxillary.msgAgentRPCConf import TEST_PORT, TURBONET_CONTROLLER_IP, TURBONET_CONTROLLER_PORT, P4_CONTROLLER_PORT, P4_CONTROLLER_IP
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.vnfiStatus import VNFIStatus
from sam.base.routingMorphic import IPV4_ROUTE_PROTOCOL, IPV6_ROUTE_PROTOCOL, ROCEV1_ROUTE_PROTOCOL, SRV6_ROUTE_PROTOCOL
from sam.base.vnf import VNF_TYPE_FORWARD, VNF_TYPE_FW, VNF_TYPE_MONITOR, VNF_TYPE_LB, VNF_TYPE_NAT, VNF_TYPE_RATELIMITER, VNF_TYPE_VPN
from sam.base.acl import ACLTable, ACLTuple, ACL_ACTION_ALLOW, ACL_ACTION_DENY, ACL_PROTO_TCP, ACL_PROTO_ICMP, ACL_PROTO_IGMP, ACL_PROTO_IPIP, ACL_PROTO_UDP
from sam.base.rateLimiter import RateLimiterConfig
from sam.base.monitorStatistic import MonitorStatistics
from sam.base.path import DIRECTION0_PATHID_OFFSET, DIRECTION1_PATHID_OFFSET, MAPPING_TYPE_MMLPSFC, ForwardingPathSet
from sam.switchController.base.p4ClassifierEntry import P4ClassifierEntry
from sam.switchController.base.p4Action import ACTION_TYPE_DECAPSULATION_NSH, ACTION_TYPE_ENCAPSULATION_NSH, ACTION_TYPE_FORWARD, FIELD_TYPE_ETHERTYPE, FIELD_TYPE_MDTYPE, FIELD_TYPE_NEXT_PROTOCOL, FIELD_TYPE_SI, FIELD_TYPE_SPI, P4Action, FieldValuePair
from sam.switchController.base.p4Match import ETH_TYPE_IPV4, ETH_TYPE_NSH, P4Match, ETH_TYPE_IPV6, ETH_TYPE_ROCEV1
from sam.switchController.base.p4RouteEntry import P4RouteEntry

from sam.base.sfcConstant import SFC_DIRECTION_0, SFC_DIRECTION_1

P4CONTROLLER_P4_SWITCH_ID_1 = 20
P4CONTROLLER_P4_SWITCH_ID_2 = 21
DIRECTION_MASK_0 = 8388607
DIRECTION_MASK_1 = 8388608
SI_PORT_MAP = [128, 136, 144, 152, 160, 168, 176, 184, 60, 52]

class P4Controller(object):
    def __init__(self, _zonename):
        # message init
        logConf = LoggerConfigurator(__name__, './log', 'p4Controller.log', level='debug')
        self.logger = logConf.getLogger()
        self.logger.info('Initialize P4 controller.')
        self.zonename = _zonename
        self._messageAgent = MessageAgent()
        self.queueName = self._messageAgent.genQueueName(P4CONTROLLER_QUEUE, _zonename)
        self._messageAgent.startRecvMsg(self.queueName)
        self._messageAgent.startMsgReceiverRPCServer(P4_CONTROLLER_IP, P4_CONTROLLER_PORT)
        self._commands = {}
        self._commandresults = {}
        self._sfclist = {}
        self._p4agent = {}
        self._p4monitor = {} # monitorstatus list
        self._sfcilist = {}
        self._sfcidir = {} # directions of sfcilist
        self._p4agent[0] = P4Agent('192.168.100.6:50052')
        # self._p4agent[1] = P4Agent('192.168.100.4:50052')
        self.logger.info('P4 controller initialization complete.')

    def getintvalfromstr(self, _addr):
        if _addr.find(':') != -1:
            return int(hexlify(socket.inet_pton(socket.AF_INET6, _addr)), 16), (1 << 128) - 1
        elif _addr.find('.') != -1:
            return int(hexlify(socket.inet_pton(socket.AF_INET, _addr)), 16), (1 << 32) - 1
        else:
            return None, None

    def getmsk(self, _addrstr, _routemorphic):
        if _addrstr == None:
            if _routemorphic == IPV4_ROUTE_PROTOCOL:
                return '0.0.0.0', '0.0.0.0'
            else:
                return '::', '::'
        adrlst = _addrstr.split('/')
        addr = adrlst[0]
        msk = '::'
        if addr.find(':') != -1:
            msklen = 128
            if len(adrlst) == 2:
                msklen = int(adrlst[1])
            binarray = '1' * msklen + '0' * (128 - msklen)
            mskval = []
            for i in range(8):
                hexstr = hex(int(binarray[i * 16: i * 16 + 16], 2))
                mskval.append(hexstr[2:])
            msk = ':'.join(mskval)
        else:
            msklen = 32
            if len(adrlst) == 2:
                msklen = int(adrlst[1])
            binarray = '1' * msklen + '0' * (32 - msklen)
            mskval = []
            for i in range(4):
                mskval.append(str(int(binarray[i * 8: i * 8 + 8], 2)))
            msk = '.'.join(mskval)
        return addr, msk

    def run(self):
        lastupdatetime = time.time()
        while True:
            msg = self._messageAgent.getMsg(self.queueName)
            msgType = msg.getMessageType()
            if msgType == None:
                msg = self._messageAgent.getMsgByRPC(P4_CONTROLLER_IP, P4_CONTROLLER_PORT)
                msgType = msg.getMessageType()
                if msgType == None:
                    while self._p4agent[0].waitForDigenst():
                        p4src = self._p4agent[0].res_src
                        p4dst = self._p4agent[0].res_dst
                        p4spi = self._p4agent[0].res_spi
                        p4si = self._p4agent[0].res_si
                        if self._p4monitor[(p4spi, p4si)].hasEntry(p4src, p4dst):
                            self.logger.info('New Monitor Entry Detected: p4id - 0, spi - %x, si - %d.' % (p4spi, p4si))
                            self.logger.info('New Monitor Entry Detected: src - %x, dst - %x.' % (p4src, p4dst))
                            self._p4monitor[(p4spi, p4si)].addEntry(p4src, p4dst)
                            self._p4agent[0].addMonitorEntry()
                    '''
                    while self._p4agent[1].waitForDigenst():
                        p4src = self._p4agent[1].res_src
                        p4dst = self._p4agent[1].res_dst
                        p4spi = self._p4agent[1].res_spi
                        p4si = self._p4agent[1].res_si
                        if self._p4monitor[(p4spi, p4si)].hasEntry(p4src, p4dst):
                            self.logger.info('New Monitor Entry Detected: p4id - 1, spi - %x, si - %d.' % (p4spi, p4si))
                            self.logger.info('New Monitor Entry Detected: src - %x, dst - %x.' % (p4src, p4dst))
                            self._p4monitor[(p4spi, p4si)].addEntry(p4src, p4dst)
                            self._p4agent[1].addMonitorEntry()
                    '''
                    if time.time() - lastupdatetime > 5.0:
                        self._updatemonitor()
                        lastupdatetime = time.time()
                elif msgType == MSG_TYPE_P4CONTROLLER_CMD:
                    self.logger.info('Got a command from rpc')
                    cmd = msg.getbody()
                    source = msg.getSource()
                    self._commands[cmd.cmdID] = cmd
                    self._commandresults[cmd.cmdID] = CMD_STATE_PROCESSING
                    resdict = {}
                    success = True
                    if cmd.cmdType == CMD_TYPE_GET_SFCI_STATE:
                        success, resdict = self._getstate()
                    else:
                        self.logger.error("Unsupported cmd type for P4 controller: %s." % cmd.cmdType)
                    if success:
                        self._commandresults[cmd.cmdID] = CMD_STATE_SUCCESSFUL
                    else:
                        self._commandresults[cmd.cmdID] = CMD_STATE_FAIL
                    cmdreply = CommandReply(cmd.cmdID, self._commandresults[cmd.cmdID])
                    cmdreply.attributes["zone"] = TURBONET_ZONE
                    cmdreply.attributes.update(resdict)
                    replymessage = SAMMessage(MSG_TYPE_P4CONTROLLER_CMD_REPLY, cmdreply)
                    self._messageAgent.sendMsgByRPC(source['srcIP'], source['srcPort'], replymessage)
            elif msgType == MSG_TYPE_P4CONTROLLER_CMD:
                self.logger.info('Got a command.')
                cmd = msg.getbody()
                self._commands[cmd.cmdID] = cmd
                self._commandresults[cmd.cmdID] = CMD_STATE_PROCESSING
                resdict = {}
                success = True
                self.logger.info('Command Type: %s.' % cmd.cmdType)
                if cmd.cmdType == CMD_TYPE_ADD_SFC:
                    success = True
                elif cmd.cmdType == CMD_TYPE_DEL_SFC:
                    success = True
                elif cmd.cmdType == CMD_TYPE_ADD_SFCI:
                    success1 = self._addsfc(cmd)
                    success2 = self._addsfci(cmd)
                    success = success1 & success2
                elif cmd.cmdType == CMD_TYPE_DEL_SFCI:
                    success1 = self._delsfc(cmd)
                    success2 = self._delsfci(cmd)
                    success = success1 & success2
                else:
                    self.logger.error("Unsupported cmd type for P4 controller: %s." % cmd.cmdType)
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
        sfc = _cmd.attributes['sfc']
        hasdir0 = False
        hasdir1 = False
        directions = sfc.directions
        if directions[0]['ID'] == SFC_DIRECTION_0:
            hasdir0 = True
        else:
            hasdir1 = True
        if len(directions) == 2:
            if directions[1]['ID'] == SFC_DIRECTION_0:
                hasdir0 = True
            else:
                hasdir1 = True
        sfci = _cmd.attributes['sfci']
        sfciID = sfci.sfciID
        nfseq = sfci.vnfiSequence
        si = len(nfseq)
        self.logger.info('Adding SFC: id - %s, hasdir0 - %d, hasdir1 - %d.' % (sfciID, hasdir0, hasdir1))
        fpset = sfci.forwardingPathSet.primaryForwardingPath
        self.logger.info('Adding SFC: Adding Turbonet Route Entries.')
        ignextnode = {}
        if hasdir0:
            self.logger.info('Adding SFC: Adding Turbonet Direction 0 Route Entries.')
            lst = fpset[DIRECTION0_PATHID_OFFSET]
            segidx = 0
            for segpath in lst:
                segidx += 1
                pathlen = len(segpath)
                for i in range(pathlen - 1):
                    fromnode = segpath[i][1]
                    tonode = segpath[i + 1][1]
                    if segidx == 1 and i == 0:
                        ignextnode[SFC_DIRECTION_0] = tonode
                        self.logger.info('Adding SFC: Found Direction 0 Nextnode For Ingress: node - %d.' % tonode)
                        continue
                    self.logger.info('Adding SFC: Adding One Segment: idx - %d, from - %d, to - %d.' % (i, fromnode, tonode))
                    if fromnode == tonode:
                        continue
                    p4M = P4Match(ETH_TYPE_NSH, src = None, dst = None)
                    p4A = P4Action(actionType = ACTION_TYPE_FORWARD, nextNodeID = tonode, newFieldValueList = None)
                    p4RE = P4RouteEntry(nodeID = fromnode, match = p4M, action = p4A)
                    routecmd = Command(CMD_TYPE_ADD_NSH_ROUTE, uuid.uuid1(), attributes = p4RE)
                    routemsg = SAMMessage(MSG_TYPE_TURBONET_CONTROLLER_CMD, routecmd)
                    self._messageAgent.sendMsgByRPC(TURBONET_CONTROLLER_IP, TURBONET_CONTROLLER_PORT, routemsg)
        if hasdir1:
            self.logger.info('Adding SFC: Adding Turbonet Direction 1 Route Entries.')
            lst = fpset[DIRECTION1_PATHID_OFFSET]
            segidx = 0
            for segpath in lst:
                segidx += 1
                pathlen = len(segpath)
                for i in range(pathlen - 1):
                    fromnode = segpath[i][1]
                    tonode = segpath[i + 1][1]
                    if segidx == 1 and i == 0:
                        ignextnode[SFC_DIRECTION_1] = tonode
                        self.logger.info('Adding SFC: Found Direction 1 Nextnode For Ingress: node - %d.' % tonode)
                        continue
                    self.logger.info('Adding SFC: Adding One Segment: idx - %d, from - %d, to - %d.' % (i, fromnode, tonode))
                    if fromnode == tonode:
                        continue
                    p4M = P4Match(ETH_TYPE_NSH, src = None, dst = None)
                    p4A = P4Action(actionType = ACTION_TYPE_FORWARD, nextNodeID = tonode, newFieldValueList = None)
                    p4RE = P4RouteEntry(nodeID = fromnode, match = p4M, action = p4A)
                    routecmd = Command(CMD_TYPE_ADD_NSH_ROUTE, uuid.uuid1(), attributes = p4RE)
                    routemsg = SAMMessage(MSG_TYPE_TURBONET_CONTROLLER_CMD, routecmd)
                    self._messageAgent.sendMsgByRPC(TURBONET_CONTROLLER_IP, TURBONET_CONTROLLER_PORT, routemsg)
        self.logger.info('Adding SFC: Adding Turbonet Classifier Entries.')
        for diri in directions:
            direthertype = ETH_TYPE_IPV4
            ignode = -1
            egnode = -1
            if isinstance(diri['ingress'], Switch):
                if diri['ingress'].programmable:
                    ignode = diri['ingress'].getNodeID()
            if isinstance(diri['egress'], Switch):
                if diri['egress'].programmable:
                    egnode = diri['egress'].getNodeID()
            egnextnode = 10000
            if diri['destination']['node'] != None:
                if isinstance(diri['destination']['node'], Switch) or isinstance(diri['destination']['node'], Server):
                    egnextnode = diri['destination']['node'].getNodeID()
            matchaddrsrc, matchaddrsrcmask = self.getintvalfromstr(diri['match']['srcIP'])
            matchaddrdst, matchaddrdstmask = self.getintvalfromstr(diri['match']['dstIP'])
            self.logger.info('Adding SFC: Classifier: proto - %x, SPI - %x, SI - %d.' % (direthertype, sfciID, si))
            if matchaddrsrc != None:
                self.logger.info('Adding SFC: Classifier: src - %x, msk - %x.' % (matchaddrsrc, matchaddrsrcmask))
            if matchaddrdst != None:
                self.logger.info('Adding SFC: Classifier: dst - %x, msk - %x.' % (matchaddrdst, matchaddrdstmask))
            self.logger.info('Adding SFC: Node Info: inode - %d, enode - %d, inode(next) - %d, enode(next) - %d.' % (ignode, egnode, ignextnode[diri['ID']], egnextnode))
            if ignode != -1:
                p4M = P4Match(direthertype, src = matchaddrsrc, dst = matchaddrdst, srcMask = matchaddrsrcmask, dstMask = matchaddrdstmask)
                fVPList = [
                    FieldValuePair(FIELD_TYPE_SPI, sfciID),
                    FieldValuePair(FIELD_TYPE_SI, si),
                    FieldValuePair(FIELD_TYPE_NEXT_PROTOCOL, direthertype),
                    FieldValuePair(FIELD_TYPE_MDTYPE, 0x1)
                ]
                p4A = P4Action(actionType = ACTION_TYPE_ENCAPSULATION_NSH, nextNodeID = ignextnode[diri['ID']], newFieldValueList = fVPList)
                p4CE = P4ClassifierEntry(nodeID = ignode, match = p4M, action = p4A)
                classifiercmd = Command(CMD_TYPE_ADD_CLASSIFIER_ENTRY, uuid.uuid1(), attributes = p4CE)
                classifiermsg = SAMMessage(MSG_TYPE_TURBONET_CONTROLLER_CMD, classifiercmd)
                self._messageAgent.sendMsgByRPC(TURBONET_CONTROLLER_IP, TURBONET_CONTROLLER_PORT, classifiermsg)
            if egnode != -1:
                p4M = P4Match(ETH_TYPE_NSH, nsh = ((sfciID << 8) + si))
                fVPList = [
                    FieldValuePair(FIELD_TYPE_ETHERTYPE, direthertype)
                ]
                p4A = P4Action(actionType = ACTION_TYPE_DECAPSULATION_NSH, nextNodeID = egnextnode, newFieldValueList = fVPList)
                p4CE = P4ClassifierEntry(nodeID = egnode, match = p4M, action=p4A)
                classifiercmd = Command(CMD_TYPE_ADD_CLASSIFIER_ENTRY, uuid.uuid1(), attributes = p4CE)
                classifiermsg = SAMMessage(MSG_TYPE_TURBONET_CONTROLLER_CMD, classifiercmd)
                self._messageAgent.sendMsgByRPC(TURBONET_CONTROLLER_IP, TURBONET_CONTROLLER_PORT, classifiermsg)
        self.logger.info('Adding SFC: Finished.')
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
        self.logger.info('Adding SFCI: sfciid - %s, hasdir0 - %d, hasdir1 - %d.' % (sfciID, hasdir0, hasdir1))
        nfseq = sfci.vnfiSequence
        si = len(nfseq)
        spi = sfciID
        self._sfcidir[spi] = (hasdir0, hasdir1)
        self._sfcilist[spi] = sfci
        routemorphic = sfci.routingMorphic.morphicName
        self.logger.info('Adding SFCI: Routing Morphic - %s.' % routemorphic)
        for nf in nfseq:
            eport = SI_PORT_MAP[si - 1]
            for nfi in nf:
                if isinstance(nfi.node, Switch):
                    p4id = -1
                    if nfi.node.switchID == P4CONTROLLER_P4_SWITCH_ID_1:
                        p4id = 0
                    elif nfi.node.switchID == P4CONTROLLER_P4_SWITCH_ID_2:
                        p4id = 1
                    else:
                        continue
                    self.logger.info('Adding SFCI: SFCI Info: si - %d, eport - %d, p4id - %d.' % (si, eport, p4id))
                    if nfi.vnfType == VNF_TYPE_FW:
                        if hasdir0:
                            self._p4agent[p4id].addIEGress(_service_path_index = (spi & DIRECTION_MASK_0), _service_index = si, _outport = eport)
                            fwlst = nfi.config.getRulesList(routemorphic)
                            self.logger.info('Adding SFCI: Adding Direction 0 Firewall with Protocol %s.' % routemorphic)
                            for aclins in fwlst:
                                proto = aclins.proto
                                isdrop = (aclins.action == ACL_ACTION_DENY)
                                srcaddr, srcmsk = self.getmsk(aclins.srcAddr, routemorphic)
                                dstaddr, dstmsk = self.getmsk(aclins.dstAddr, routemorphic)
                                self.logger.info('Adding SFCI: Adding Direction 0 Firewall Entry: spi - %x, si - %d, action - %d.' % (spi, si, aclins.action))
                                self.logger.info('Adding SFCI: Adding Direction 0 Firewall Entry: src - %s, msk - %s.' % (srcaddr, srcmsk))
                                self.logger.info('Adding SFCI: Adding Direction 0 Firewall Entry: dst - %s, msk - %s.' % (dstaddr, dstmsk))
                                if routemorphic == IPV4_ROUTE_PROTOCOL:
                                    self._p4agent[p4id].addv4FWentry(
                                        _service_path_index = (spi & DIRECTION_MASK_0), _service_index = si,
                                        _src_addr = srcaddr, _dst_addr = dstaddr, _src_mask = srcmsk, _dst_mask = dstmsk,
                                        _nxt_hdr = proto, _priority = 0, _is_drop = isdrop
                                    )
                                else:
                                    self._p4agent[p4id].addv6FWentry(
                                        _service_path_index = (spi & DIRECTION_MASK_0), _service_index = si,
                                        _src_addr = srcaddr, _dst_addr = dstaddr, _src_mask = srcmsk, _dst_mask = dstmsk,
                                        _nxt_hdr = proto,  _priority = 0, _is_drop = isdrop
                                    )
                        if hasdir1:
                            self._p4agent[p4id].addIEGress(_service_path_index = (spi | DIRECTION_MASK_1), _service_index = si, _outport = eport)
                            fwlst = nfi.config.getRulesList(routemorphic)
                            self.logger.info('Adding SFCI: Adding Direction 1 Firewall with Protocol %s.' % routemorphic)
                            for aclins in fwlst:
                                proto = aclins.proto
                                isdrop = (aclins.action == ACL_ACTION_DENY)
                                srcaddr, srcmsk = self.getmsk(aclins.srcAddr, routemorphic)
                                dstaddr, dstmsk = self.getmsk(aclins.dstAddr, routemorphic)
                                self.logger.info('Adding SFCI: Adding Direction 1 Firewall Entry: spi - %x, si - %d, action - %d.' % (spi, si, aclins.action))
                                self.logger.info('Adding SFCI: Adding Direction 1 Firewall Entry: src - %s, msk - %s.' % (srcaddr, srcmsk))
                                self.logger.info('Adding SFCI: Adding Direction 1 Firewall Entry: dst - %s, msk - %s.' % (dstaddr, dstmsk))
                                if routemorphic == IPV4_ROUTE_PROTOCOL:
                                    self._p4agent[p4id].addv4FWentry(
                                        _service_path_index = (spi | DIRECTION_MASK_1), _service_index = si,
                                        _src_addr = srcaddr, _dst_addr = dstaddr, _src_mask = srcmsk, _dst_mask = dstmsk,
                                        _nxt_hdr = proto, _priority = 0, _is_drop = isdrop
                                    )
                                else:
                                    self._p4agent[p4id].addv6FWentry(
                                        _service_path_index = (spi | DIRECTION_MASK_1), _service_index = si,
                                        _src_addr = srcaddr, _dst_addr = dstaddr, _src_mask = srcmsk, _dst_mask = dstmsk,
                                        _nxt_hdr = proto, _priority = 0, _is_drop = isdrop
                                    )
                    elif nfi.vnfType == VNF_TYPE_RATELIMITER:
                        ratelim = nfi.config.maxMbps * 1024
                        self.logger.info('Adding SFCI: Adding RateLimiter with limit %d (Mbps).' % nfi.config.maxMbps)
                        if hasdir0:
                            self._p4agent[p4id].addIEGress(_service_path_index = (spi & DIRECTION_MASK_0), _service_index = si, _outport = eport)
                            self._p4agent[p4id].addRateLimiter(_service_path_index = (spi & DIRECTION_MASK_0), _service_index = si)
                            self._p4agent[p4id].editRateLimiter(
                                _service_path_index = (spi & DIRECTION_MASK_0), _service_index = si,
                                _cir = ratelim, _cbs = ratelim, _pir = ratelim, _pbs = ratelim
                            )
                        if hasdir1:
                            self._p4agent[p4id].addIEGress(_service_path_index = (spi | DIRECTION_MASK_1), _service_index = si, _outport = eport)
                            self._p4agent[p4id].addRateLimiter(_service_path_index = (spi | DIRECTION_MASK_1), _service_index = si)
                            self._p4agent[p4id].editRateLimiter(
                                _service_path_index = (spi | DIRECTION_MASK_1), _service_index = si,
                                _cir = ratelim, _cbs = ratelim, _pir = ratelim, _pbs = ratelim
                            )
                    elif nfi.vnfType == VNF_TYPE_MONITOR:
                        if hasdir0:
                            self.logger.info('Adding SFCI: Adding Direction 0 Monitor: spi - %x, si - %d.' % (spi, si))
                            self._p4agent[p4id].addIEGress(_service_path_index = (spi & DIRECTION_MASK_0), _service_index = si, _outport = eport)
                            self._p4monitor[((spi & DIRECTION_MASK_0), si)] = P4MonitorStatus((spi & DIRECTION_MASK_0), si, routemorphic, p4id)
                            if routemorphic == IPV4_ROUTE_PROTOCOL:
                                self._p4agent[p4id].addMonitorv4(_service_path_index = (spi & DIRECTION_MASK_0), _service_index = si)
                            else:
                                self._p4agent[p4id].addMonitorv6(_service_path_index = (spi & DIRECTION_MASK_0), _service_index = si)
                        if hasdir1:
                            self.logger.info('Adding SFCI: Adding Direction 1 Monitor: spi - %x, si - %d.' % (spi, si))
                            self._p4agent[p4id].addIEGress(_service_path_index = (spi | DIRECTION_MASK_1), _service_index = si, _outport = eport)
                            self._p4monitor[((spi | DIRECTION_MASK_1), si)] = P4MonitorStatus((spi | DIRECTION_MASK_1), si, routemorphic, p4id)
                            if routemorphic == IPV4_ROUTE_PROTOCOL:
                                self._p4agent[p4id].addMonitorv4(_service_path_index = (spi | DIRECTION_MASK_1), _service_index = si)
                            else:
                                self._p4agent[p4id].addMonitorv6(_service_path_index = (spi | DIRECTION_MASK_1), _service_index = si)
                    else:
                        return False
            si = si - 1
        self.logger.info('Adding SFCI: Finished.')
        return True
    
    def _getstate(self):
        self.logger.info('Getting SFCI State: Started.')
        for spi in self._sfcilist.keys():
            sfci = self._sfcilist[spi]
            nfseq = sfci.vnfiSequence
            si = len(nfseq)
            routemorphic = sfci.routingMorphic.morphicName
            (hasdir0, hasdir1) = self._sfcidir[spi]
            self.logger.info('Getting SFCI State: SFCI Info: spi - %x, si - %d, proto - %s, hasdir0 - %d, hasdir1 - %d.' % (spi, si, routemorphic, hasdir0, hasdir1))
            for nfs in nfseq:
                for nfi in nfs:
                    if isinstance(nfi.node, Switch):
                        p4id = -1
                        if nfi.node.switchID == P4CONTROLLER_P4_SWITCH_ID_1:
                            p4id = 0
                        elif nfi.node.switchID == P4CONTROLLER_P4_SWITCH_ID_2:
                            p4id = 1
                        else:
                            continue
                        ingpkt = {}
                        egpkt = {}
                        ingbyte = {}
                        egbyte = {}
                        stat = None
                        ingpkt_temp, ingbyte_temp, egpkt_temp, egbyte_temp = 0, 0, 0, 0
                        if hasdir0:
                            ingpkt_temp, ingbyte_temp, egpkt_temp, egbyte_temp = self._p4agent[p4id].queryIOamount((spi & DIRECTION_MASK_0), si)
                            self.logger.info('Getting SFCI State: Direction 0 Status: ingpkt - %d, ingbyte - %d.' % (ingpkt_temp, ingbyte_temp))
                            self.logger.info('Getting SFCI State: Direction 0 Status: egpkt - %d, egbyte - %d.' % (egpkt_temp, egbyte_temp))
                        ingpkt[SFC_DIRECTION_0] = ingpkt_temp
                        ingbyte[SFC_DIRECTION_0] = ingbyte_temp
                        egpkt[SFC_DIRECTION_0] = egpkt_temp
                        egbyte[SFC_DIRECTION_0] = egbyte_temp
                        if hasdir1:
                            ingpkt_temp, ingbyte_temp, egpkt_temp, egbyte_temp = self._p4agent[p4id].queryIOamount((spi | DIRECTION_MASK_1), si)
                            self.logger.info('Getting SFCI State: Direction 1 Status: ingpkt - %d, ingbyte - %d.' % (ingpkt_temp, ingbyte_temp))
                            self.logger.info('Getting SFCI State: Direction 1 Status: egpkt - %d, egbyte - %d.' % (egpkt_temp, egbyte_temp))
                        ingpkt[SFC_DIRECTION_1] = ingpkt_temp
                        ingbyte[SFC_DIRECTION_1] = ingbyte_temp
                        egpkt[SFC_DIRECTION_1] = egpkt_temp
                        egbyte[SFC_DIRECTION_1] = egbyte_temp
                        if nfi.vnfType == VNF_TYPE_MONITOR:
                            stat = MonitorStatistics()
                            self.logger.info('Getting SFCI State: Getting Monitor Stat: spi - %x, si - %d.' % (spi, si))
                            if hasdir0:
                                reslst = self._p4monitor[((spi & DIRECTION_MASK_0), si)].getStat()
                                for resentry in reslst:
                                    addrpair = None
                                    if routemorphic == IPV4_ROUTE_PROTOCOL:
                                        addrpair = SrcDstPair(ipaddress.IPv4Address(resentry.src), ipaddress.IPv4Address(resentry.dst), IPV4_ROUTE_PROTOCOL)
                                    else:
                                        addrpair = SrcDstPair(ipaddress.IPv6Address(resentry.src), ipaddress.IPv6Address(resentry.dst), routemorphic)
                                    self.logger.info('Getting SFCI State: Dir 0 Monitor Entry: src - %x, dst - %x.' % (resentry.src, resentry.dst))
                                    self.logger.info('Getting SFCI State: Dir 0 Monitor Entry: pktrate - %x, byterate - %x.' % (resentry.pktrate, resentry.byterate))
                                    stat.addStatistic(
                                        directionID = SFC_DIRECTION_0,
                                        srcDstPair = addrpair,
                                        pktRate = resentry.pktrate,
                                        bytesRate = resentry.byterate
                                    )
                            if hasdir1:
                                reslst = self._p4monitor[((spi | DIRECTION_MASK_1), si)].getStat()
                                for resentry in reslst:
                                    addrpair = None
                                    if routemorphic == IPV4_ROUTE_PROTOCOL:
                                        addrpair = SrcDstPair(ipaddress.IPv4Address(resentry.src), ipaddress.IPv4Address(resentry.dst), IPV4_ROUTE_PROTOCOL)
                                    else:
                                        addrpair = SrcDstPair(ipaddress.IPv6Address(resentry.src), ipaddress.IPv6Address(resentry.dst), routemorphic)
                                    self.logger.info('Getting SFCI State: Dir 1 Monitor Entry: src - %x, dst - %x.' % (resentry.src, resentry.dst))
                                    self.logger.info('Getting SFCI State: Dir 1 Monitor Entry: pktrate - %x, byterate - %x.' % (resentry.pktrate, resentry.byterate))
                                    stat.addStatistic(
                                        directionID = SFC_DIRECTION_1,
                                        srcDstPair = addrpair,
                                        pktRate = resentry.pktrate,
                                        bytesRate = resentry.byterate
                                    )
                        else:
                            stat = nfi.config
                        nfi.vnfiStatus = VNFIStatus(
                            inputTrafficAmount = ingbyte, inputPacketAmount = ingpkt,
                            outputTrafficAmount = egbyte, outputPacketAmount = egpkt,
                            state = stat
                        )
                si = si - 1
        self.logger.info('Getting SFCI State: Finished.')
        return True, {'sfcisDict': self._sfcilist}
    
    def _delsfc(self, _cmd):
        sfc = _cmd.attributes['sfc']
        hasdir0 = False
        hasdir1 = False
        directions = sfc.directions
        if directions[0]['ID'] == SFC_DIRECTION_0:
            hasdir0 = True
        else:
            hasdir1 = True
        if len(directions) == 2:
            if directions[1]['ID'] == SFC_DIRECTION_0:
                hasdir0 = True
            else:
                hasdir1 = True
        sfci = _cmd.attributes['sfci']
        sfciID = sfci.sfciID
        nfseq = sfci.vnfiSequence
        si = len(nfseq)
        self.logger.info('Deleting SFC: id - %s, hasdir0 - %d, hasdir1 - %d.' % (sfciID, hasdir0, hasdir1))
        fpset = sfci.forwardingPathSet.primaryForwardingPath
        self.logger.info('Deleting SFC: Deleting Turbonet Route Entries.')
        ignextnode = {}
        if hasdir0:
            self.logger.info('Deleting SFC: Deleting Turbonet Direction 0 Route Entries.')
            lst = fpset[DIRECTION0_PATHID_OFFSET]
            segidx = 0
            for segpath in lst:
                segidx += 1
                pathlen = len(segpath)
                for i in range(pathlen - 1):
                    fromnode = segpath[i][1]
                    tonode = segpath[i + 1][1]
                    if segidx == 1 and i == 0:
                        ignextnode[SFC_DIRECTION_0] = tonode
                        self.logger.info('Deleting SFC: Found Direction 0 Nextnode For Ingress: node - %d.' % tonode)
                        continue
                    self.logger.info('Deleting SFC: Deleting One Segment: idx - %d, from - %d, to - %d.' % (i, fromnode, tonode))
                    if fromnode == tonode:
                        continue
                    p4M = P4Match(ETH_TYPE_NSH, src = None, dst = None)
                    p4A = P4Action(actionType = ACTION_TYPE_FORWARD, nextNodeID = tonode, newFieldValueList = None)
                    p4RE = P4RouteEntry(nodeID = fromnode, match = p4M, action = p4A)
                    routecmd = Command(CMD_TYPE_DEL_NSH_ROUTE, uuid.uuid1(), attributes = p4RE)
                    routemsg = SAMMessage(MSG_TYPE_TURBONET_CONTROLLER_CMD, routecmd)
                    self._messageAgent.sendMsgByRPC(TURBONET_CONTROLLER_IP, TURBONET_CONTROLLER_PORT, routemsg)
        if hasdir1:
            self.logger.info('Deleting SFC: Deleting Turbonet Direction 1 Route Entries.')
            lst = fpset[DIRECTION1_PATHID_OFFSET]
            segidx = 0
            for segpath in lst:
                segidx += 1
                pathlen = len(segpath)
                for i in range(pathlen - 1):
                    fromnode = segpath[i][1]
                    tonode = segpath[i + 1][1]
                    if segidx == 1 and i == 0:
                        ignextnode[SFC_DIRECTION_1] = tonode
                        self.logger.info('Deleting SFC: Found Direction 1 Nextnode For Ingress: node - %d.' % tonode)
                        continue
                    self.logger.info('Deleting SFC: Deleting One Segment: idx - %d, from - %d, to - %d.' % (i, fromnode, tonode))
                    if fromnode == tonode:
                        continue
                    p4M = P4Match(ETH_TYPE_NSH, src = None, dst = None)
                    p4A = P4Action(actionType = ACTION_TYPE_FORWARD, nextNodeID = tonode, newFieldValueList = None)
                    p4RE = P4RouteEntry(nodeID = fromnode, match = p4M, action = p4A)
                    routecmd = Command(CMD_TYPE_DEL_NSH_ROUTE, uuid.uuid1(), attributes = p4RE)
                    routemsg = SAMMessage(MSG_TYPE_TURBONET_CONTROLLER_CMD, routecmd)
                    self._messageAgent.sendMsgByRPC(TURBONET_CONTROLLER_IP, TURBONET_CONTROLLER_PORT, routemsg)
        self.logger.info('Deleting SFC: Deleting Turbonet Classifier Entries.')
        for diri in directions:
            direthertype = ETH_TYPE_IPV4
            ignode = -1
            egnode = -1
            if isinstance(diri['ingress'], Switch):
                if diri['ingress'].programmable:
                    ignode = diri['ingress'].getNodeID()
            if isinstance(diri['egress'], Switch):
                if diri['egress'].programmable:
                    egnode = diri['egress'].getNodeID()
            egnextnode = 10000
            if diri['destination']['node'] != None:
                if isinstance(diri['destination']['node'], Switch) or isinstance(diri['destination']['node'], Server):
                    egnextnode = diri['destination']['node'].getNodeID()
            matchaddrsrc, matchaddrsrcmask = self.getintvalfromstr(diri['match']['srcIP'])
            matchaddrdst, matchaddrdstmask = self.getintvalfromstr(diri['match']['dstIP'])
            self.logger.info('Deleting SFC: Classifier: proto - %x, SPI - %x, SI - %d.' % (direthertype, sfciID, si))
            if matchaddrsrc != None:
                self.logger.info('Deleting SFC: Classifier: src - %x, msk - %x.' % (matchaddrsrc, matchaddrsrcmask))
            if matchaddrdst != None:
                self.logger.info('Deleting SFC: Classifier: dst - %x, msk - %x.' % (matchaddrdst, matchaddrdstmask))
            self.logger.info('Deleting SFC: Node Info: inode - %d, enode - %d, inode(next) - %d, enode(next) - %d.' % (ignode, egnode, ignextnode[diri['ID']], egnextnode))
            if ignode != -1:
                p4M = P4Match(direthertype, src = matchaddrsrc, dst = matchaddrdst, srcMask = matchaddrsrcmask, dstMask = matchaddrdstmask)
                fVPList = [
                    FieldValuePair(FIELD_TYPE_SPI, sfciID),
                    FieldValuePair(FIELD_TYPE_SI, si),
                    FieldValuePair(FIELD_TYPE_NEXT_PROTOCOL, direthertype),
                    FieldValuePair(FIELD_TYPE_MDTYPE, 0x1)
                ]
                p4A = P4Action(actionType = ACTION_TYPE_ENCAPSULATION_NSH, nextNodeID = ignextnode[diri['ID']], newFieldValueList = fVPList)
                p4CE = P4ClassifierEntry(nodeID = ignode, match = p4M, action = p4A)
                classifiercmd = Command(CMD_TYPE_DEL_CLASSIFIER_ENTRY, uuid.uuid1(), attributes = p4CE)
                classifiermsg = SAMMessage(MSG_TYPE_TURBONET_CONTROLLER_CMD, classifiercmd)
                self._messageAgent.sendMsgByRPC(TURBONET_CONTROLLER_IP, TURBONET_CONTROLLER_PORT, classifiermsg)
            if egnode != -1:
                p4M = P4Match(ETH_TYPE_NSH, nsh = ((sfciID << 8) + si))
                fVPList = [
                    FieldValuePair(FIELD_TYPE_ETHERTYPE, direthertype)
                ]
                p4A = P4Action(actionType = ACTION_TYPE_DECAPSULATION_NSH, nextNodeID = egnextnode, newFieldValueList = fVPList)
                p4CE = P4ClassifierEntry(nodeID = egnode, match = p4M, action=p4A)
                classifiercmd = Command(CMD_TYPE_DEL_CLASSIFIER_ENTRY, uuid.uuid1(), attributes = p4CE)
                classifiermsg = SAMMessage(MSG_TYPE_TURBONET_CONTROLLER_CMD, classifiercmd)
                self._messageAgent.sendMsgByRPC(TURBONET_CONTROLLER_IP, TURBONET_CONTROLLER_PORT, classifiermsg)
        self.logger.info('Deleting SFC: Finished.')
        return True
    
    def _delsfci(self, _cmd):
        # prepare to copy from add
        return True
    
    def _updatemonitor(self):
        self.logger.info('Updating Monitor: Started.')
        for i in self._p4monitor.keys():
            p4id = self._p4monitor[i].p4id
            spi = self._p4monitor[i].service_path_index
            si = self._p4monitor[i].service_index
            proto = self._p4monitor[i].proto
            self.logger.info('Updating Monitor: Monitor Info: p4id - %d, spi - %x, si - %d, proto - %s.' % (p4id, spi, si, proto))
            entrylst = self._p4monitor[i].getEntryList()
            for mnentry in entrylst:
                pktcnt = 0
                bytecnt = 0
                timetag = time.time()
                self.logger.info('Updating Monitor: Entry Info: spi - %x, si - %d, src - %x, dst - %x.' % (spi, si, mnentry.src, mnentry.dst))
                if proto == IPV4_ROUTE_PROTOCOL:
                    pktcnt, bytecnt = self._p4agent[p4id].queryMonitorv4(spi, si, mnentry.src, mnentry.dst)
                else:
                    pktcnt, bytecnt = self._p4agent[p4id].queryMonitorv6(spi, si, mnentry.src, mnentry.dst)
                self.logger.info('Updating Monitor: Entry Result: pktcnt - %d, bytecnt - %d.' % (pktcnt, bytecnt))
                self._p4monitor[i].updateStat(mnentry.uuid, pktcnt, bytecnt)
        self.logger.info('Updating Monitor: Finished.')

if __name__ == '__main__':
    p4ctl = P4Controller('')
    p4ctl.run()
