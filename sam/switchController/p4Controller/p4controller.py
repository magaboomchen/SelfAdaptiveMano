import sam

from agent.p4Agent import P4Agent

from sam.base.command import CMD_TYPE_GET_SFCI_STATE, CommandReply, CMD_TYPE_ADD_SFCI, CMD_TYPE_DEL_SFCI, CMD_STATE_SUCCESSFUL, CMD_STATE_FAIL, CMD_STATE_PROCESSING
from sam.base.server import Server
from sam.base.switch import Switch
from sam.base.messageAgent import SAMMessage, MessageAgent, P4CONTROLLER_QUEUE, MSG_TYPE_P4CONTROLLER_CMD, MSG_TYPE_P4CONTROLLER_CMD_REPLY, MEDIATOR_QUEUE, TURBONET_ZONE
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.vnf import VNFIStatus
from sam.base.routingMorphic import IPV4_ROUTE_PROTOCOL, IPV6_ROUTE_PROTOCOL, ROCEV1_ROUTE_PROTOCOL, SRV6_ROUTE_PROTOCOL
from sam.base.vnf import VNF_TYPE_FORWARD, VNF_TYPE_FW, VNF_TYPE_MONITOR, VNF_TYPE_LB, VNF_TYPE_NAT, VNF_TYPE_RATELIMITER, VNF_TYPE_VPN
from sam.base.acl import ACLTable, ACLTuple
from sam.base.rateLimiter import RateLimiterConfig

P4CONTROLLER_P4_SWITCH_ID_1 = 20
P4CONTROLLER_P4_SWITCH_ID_2 = 21

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
        self._p4id = 20
        self._p4agent = {}
        # self._p4agent[0] = P4Agent('192.168.100.4:50052')
        # self._p4agent[1] = P4Agent('192.168.100.5:50052')
        self.logger.info('P4 controller initialization complete.')

    def run(self):
        while True:
            msg = self._messageAgent.getMsg(self.queueName)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            elif msgType == MSG_TYPE_P4CONTROLLER_CMD:
                self.logger.info('Got a command.')
                cmd = msg.getbody()
                print(msg)
                self._commands[cmd.cmdID] = cmd
                self._commandresults[cmd.cmdID] = CMD_STATE_PROCESSING
                resdict = {}
                success = True
                '''
                if cmd.cmdType == CMD_TYPE_ADD_SFC:
                    success = self._addsfc(cmd)
                elif cmd.cmdType == CMD_TYPE_DEL_SFC:
                    success = self._delsfc(cmd)
                elif cmd.cmdType == CMD_TYPE_ADD_SFCI:
                    success = self._addsfci(cmd)
                elif cmd.cmdType == CMD_TYPE_DEL_SFCI:
                    success = self._delsfci(cmd)
                elif cmd.cmdType == CMD_TYPE_GET_SFCI_STATE:
                    success, resdict = self._getstate(cmd)
                else:
                    self.logger.error("Unsupported cmd type for P4 controller: %s." % cmd.cmdType)
                if success:
                    self._commandresults[cmd.cmdID] = CMD_STATE_SUCCESSFUL
                else:
                    self._commandresults[cmd.cmdID] = CMD_STATE_FAIL
                '''
                cmdreply = CommandReply(cmd.cmdID, self._commandresults[cmd.cmdID])
                cmdreply.attributes["zone"] = self.zonename
                cmdreply.attributes.update(resdict)
                replymessage = SAMMessage(MSG_TYPE_VNF_CONTROLLER_CMD_REPLY, cmdreply)
                self._messageAgent.sendMsg(MEDIATOR_QUEUE, replymessage)
            else:
                self.logger.error('Unsupported msg type for P4 controller: %s.' % msg.getMessageType())
    
    def _addsfc(self, _cmd):
        # send turbonet command
        return True
    
    def _addsfci(self, _cmd):
        sfci = _cmd.attributes['sfci']
        sfciID = sfci.sfciID
        self.logger.info('Adding sfci %s.' % sfciID)
        nfseq = sfci.vnfiSequence
        for nf in nfseq:
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
                        self._p4agent[p4id].addIEGress()
                    elif nfi.vnfType == VNF_TYPE_RATELIMITER:
                        self._p4agent[p4id].addIEGress()
                        self._p4agent[p4id].addRateLimiter()
                    elif nfi.vnfType == VNF_TYPE_MONITOR:
                        self._p4agent[p4id].addIEGress()
                        self._p4agent[p4id].addMonitor()
                    else:
                        return False
        return True
    
    def _getstate(self, _cmd):
        return False, {}
    
    def _delsfc(self, _cmd):
        # send turbonet command
        return True
    
    def _delsfci(self, _cmd):
        sfci = _cmd.attributes['sfci']
        sfciID = sfci.sfciID
        self.logger.info('Deleting sfci %s.' % sfciID)
        nfseq = sfci.vnfiSequence
        for nf in nfseq:
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
                        self._p4agent[p4id].removeIEGress()
                    elif nfi.vnfType == VNF_TYPE_RATELIMITER:
                        self._p4agent[p4id].removeIEGress()
                        self._p4agent[p4id].removeRateLimiter()
                    elif nfi.vnfType == VNF_TYPE_MONITOR:
                        self._p4agent[p4id].removeIEGress()
                        self._p4agent[p4id].removeMonitor()
                    else:
                        return False
        return True

if __name__ == '__main__':
    p4ctl = P4Controller(TURBONET_ZONE)
    p4ctl.run()
