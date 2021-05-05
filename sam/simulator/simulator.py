#!/usr/bin/python
# -*- coding: UTF-8 -*-

import time
import uuid

import datetime

from sam.base.messageAgent import *
from sam.base.sfc import *
from sam.base.switch import *
from sam.base.server import *
from sam.base.link import *
from sam.base.vnf import *
from sam.base.command import *
from sam.base.shellProcessor import ShellProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.simulator.simulatorInfoBaseMaintainer import SimulatorInfoBaseMaintainer
from sam.base.routingMorphic import *
from sam.base.path import *
from Queue import Queue, Empty
from getopt import getopt
import random
import threading
import os


class Simulator(object):
    def __init__(self, op_input):
        logConfigur = LoggerConfigurator(__name__, './log',
                            'simulator.log', level='debug')
        self.logger = logConfigur.getLogger()
        self.logger.setLevel(logging.DEBUG)
        self.logger.info("Init simulator.")

        self._cm = CommandMaintainer()

        self._sib = SimulatorInfoBaseMaintainer()

        self._messageAgent = MessageAgent(self.logger)
        # set RabbitMqServer ip, user, passwd into your settings
        # For example, your virtual machine's ip address is 192.168.5.124
        # your rabbitmqServerUserName is "mq"
        # your rabbitmqServerUserCode is "123456"
        self._messageAgent.setRabbitMqServer("192.168.5.124", "mq", "123456")
        self._messageAgent.startRecvMsg(SIMULATOR_QUEUE)

        self.op_input=op_input

    def startSimulator(self):
        try:
            while True:
                try:
                    while True:
                        command=self.op_input.get_nowait()
                        command=command.strip()
                        if command:
                            self._op_input_handler(command)
                        self.op_input.task_done()
                except Empty:
                    pass

                msg = self._messageAgent.getMsg(SIMULATOR_QUEUE)
                msgType = msg.getMessageType()
                if msgType == None:
                    pass
                else:
                    body = msg.getbody()
                    if self._messageAgent.isCommand(body):
                        self._commandHandler(body)
                    else:
                        raise ValueError("Unknown massage body")
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, "simulator")

    def _commandHandler(self,cmd):
        self.logger.debug(" Simulator gets a command ")
        self._cm.addCmd(cmd)
        attributes={}
        try:
            if cmd.cmdType == CMD_TYPE_ADD_SFC:
                self._addSFCHandler(cmd)
            elif cmd.cmdType == CMD_TYPE_ADD_SFCI:
                self._addSFCIHandler(cmd)
            elif cmd.cmdType == CMD_TYPE_DEL_SFCI:
                self._delSFCIHandler(cmd)
            elif cmd.cmdType == CMD_TYPE_DEL_SFC:
                self._delSFCHandler(cmd)
            elif cmd.cmdType == CMD_TYPE_GET_SERVER_SET:
                attributes=self._getServerSetHandler(cmd)
            elif cmd.cmdType == CMD_TYPE_GET_TOPOLOGY:
                attributes=self._getTopologyHandler(cmd)
            # elif cmd.cmdType == CMD_TYPE_GET_SFCI_STATE:
            #     self._getSFCIStateHandler(cmd)
            elif cmd.cmdType == CMD_TYPE_GET_FLOW_SET:
                attributes=self._getFlowSetHandler(cmd)
            else:
                raise ValueError("Unkonwn command type.")
            self._cm.changeCmdState(cmd.cmdID, CMD_STATE_SUCCESSFUL)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, "simulator")
            self._cm.changeCmdState(cmd.cmdID, CMD_STATE_FAIL)
        finally:
            cmdRply = CommandReply(cmd.cmdID, self._cm.getCmdState(cmd.cmdID),dict(attributes, source='simulator'))
            rplyMsg = SAMMessage(MSG_TYPE_SIMULATOR_CMD_REPLY, cmdRply)
            self._messageAgent.sendMsg(MEDIATOR_QUEUE, rplyMsg)

    def _addSFCHandler(self, cmd):
        pass
        # TODO

    def _addSFCIHandler(self, cmd):
        sfc=cmd.attributes['sfc']
        sfcUUID=sfc.sfcUUID
        vNFTypeSequence=sfc.vNFTypeSequence
        maxScalingInstanceNumber=sfc.maxScalingInstanceNumber
        backupInstanceNumber=sfc.backupInstanceNumber
        applicationType=sfc.applicationType
        directions=sfc.directions
        for direction in directions:
            ingress=direction['ingress']
            ingressID=ingress.getServerID()
            egress=direction['egress']
            egressID=egress.getServerID()
            assert ingressID in self._sib.servers and self._sib.servers[ingressID]['server'].getServerType()==SERVER_TYPE_CLASSIFIER
            assert egressID in self._sib.servers and self._sib.servers[egressID]['server'].getServerType()==SERVER_TYPE_CLASSIFIER
        slo=sfc.slo
        latencyBound=slo.latencyBound
        throughput=slo.throughput
        routingMorphic=sfc.routingMorphic # may be None
        sfci=cmd.attributes['sfci']
        sfciID=sfci.sfciID
        vnfiSequence=sfci.vnfiSequence
        for vnfiSeqStage in vnfiSequence:
            assert len(vnfiSeqStage)==1 # no backup
            vnfi=vnfiSeqStage[0]
            vnfID=vnfi.vnfID
            vnfType=vnfi.vnfType
            vnfiID=vnfi.vnfiID
            node=vnfi.node
            if isinstance(node,Server):
                nodeID=node.getServerID()
                assert nodeID in self._sib.servers and self._sib.servers[nodeID]['server'].getServerType()==SERVER_TYPE_NFVI
            elif isinstance(node,Switch):
                nodeID=node.switchID
                assert node.programmable
                assert nodeID in self._sib.switches
            else:
                raise ValueError('vnfi node is neither server nor switch')
        forwardingPathSet=sfci.forwardingPathSet
        mappingType=forwardingPathSet.mappingType
        primaryForwardingPath=forwardingPathSet.primaryForwardingPath
        assert len(primaryForwardingPath)==len(directions)
        for direction in directions:
            dirID=direction['ID']
            if dirID==0:
                pathlist=primaryForwardingPath[DIRECTION1_PATHID_OFFSET]
            elif dirID==1:
                pathlist=primaryForwardingPath[DIRECTION2_PATHID_OFFSET]
            assert len(pathlist)==len(vnfiSequence)+1
            ingress=direction['ingress']
            ingressID=ingress.getServerID()
            egress=direction['egress']
            egressID=egress.getServerID()
            assert ingressID==pathlist[0][0][1]
            assert (pathlist[0][0][1],pathlist[0][1][1]) in self._sib.serverLinks
            assert egressID==pathlist[-1][-1][1]
            assert (pathlist[-1][-2][1],pathlist[-1][-1][1]) in self._sib.serverLinks
            for i,vnfiSeqStage in enumerate(vnfiSequence):
                vnfi=vnfiSeqStage[0] # no backup
                node=vnfi.node
                if isinstance(node,Server):
                    nodeID=node.getServerID()
                elif isinstance(node,Switch):
                    nodeID=node.switchID
                assert pathlist[i][-1][1]==nodeID
                assert pathlist[i+1][0][1]==nodeID
                if isinstance(node,Server):
                    assert (pathlist[i][-2][1],pathlist[i][-1][1]) in self._sib.serverLinks
                    assert (pathlist[i+1][0][1],pathlist[i+1][1][1]) in self._sib.serverLinks
                elif isinstance(node,Switch):
                    assert (pathlist[i][-2][1],pathlist[i][-1][1]) in self._sib.links
                    assert (pathlist[i+1][0][1],pathlist[i+1][1][1]) in self._sib.links
            for path in pathlist:
                for _,switchID in path[1:-1]:
                    assert switchID in self._sib.switches
                for i in range(1, len(path)-2):
                    assert (path[i][1],path[i+1][1]) in self._sib.links

        # TODO
        # check resources
        # assign resources
        # store information
        self._sib.sfcs[sfcUUID]={'sfc':sfc}
        self._sib.sfcis[sfciID]={'sfc':sfc, 'sfci':sfci, 'traffics':set()}

    def _delSFCIHandler(self, cmd):
        sfc=cmd.attributes['sfc']
        sfci=cmd.attributes['sfci']
        # TODO
        # release resources
        # purge information
        for trafficID in self._sib.sfcis[sfciID]['traffics']:
            self._sib.flows.pop(trafficID)
        self._sib.sfcis.pop(sfciID)

    def _delSFCHandler(self, cmd):
        pass
        # TODO

    def _getServerSetHandler(self, cmd):
        # format ref: SeverManager.serverSet, SeverManager._storeServerInfo
        result={}
        for serverID, serverInfo in self._sib.servers.items():
            result[serverID]={'server':serverInfo['server'], 'Active':serverInfo['Active'], 'timestamp':serverInfo['timestamp']}
        return {'servers': result}

    def _getTopologyHandler(self, cmd):
        # see ryu/topoCollector.py -> TopoCollector.get_topology_handler
        switches={}
        for switchID, switchInfo in self._sib.switches.items():
            switches[switchID]={'switch': switchInfo['switch'], 'Active':switchInfo['Active']}
        links={}
        for (srcNodeID, dstNodeID), linkInfo in self._sib.links.items():
            links[(srcNodeID, dstNodeID)]={'link': linkInfo['link'], 'Active': linkInfo['Active']}
        return {'switches': switches, 'links': links}

    # def _getSFCIStateHandler(self, cmd):
    #     pass
    #     # TODO

    def _getFlowSetHandler(self, cmd):
        result={}
        return {'flows': result}

    def _op_input_handler(self, cmdstr):
        self.logger.debug('Simulator received operator input: '+cmdstr)
        try:
            cmdtype=cmdstr.split(' ',1)[0].lower()
            if cmdtype=='reset':
                opt, arg = getopt(cmdstr.split(' ')[1:],'',())
                if not opt and not arg: # reset
                    self._sib.reset()
                else:
                    raise ValueError(cmdtype+' '+cmdstr)
            elif cmdtype=='load':
                opt, arg = getopt(cmdstr.split(' ')[1:],'',())
                if not opt and len(arg)==1: # load <filename>
                    self._sib.loadTopology(arg[0])
                else:
                    raise ValueError(cmdtype+' '+cmdstr)
            elif cmdtype=='server':
                opt, arg = getopt(cmdstr.split(' ')[1:],'',())
                if not opt and len(arg)==2 and arg[1] in ('up','down'): # server <serverID> up|down
                    serverID=int(arg[0])
                    self._sib.servers[serverID]['Active']=(arg[1].lower()=='up')
                else:
                    raise ValueError(cmdtype+' '+cmdstr)
            elif cmdtype=='switch':
                opt, arg = getopt(cmdstr.split(' ')[1:],'',())
                if not opt and len(arg)==2 and arg[1] in ('up','down'): # switch <switchID> up|down
                    switchID=int(arg[0])
                    self._sib.switches[switchID]['Active']=(arg[1].lower()=='up')
                else:
                    raise ValueError(cmdtype+' '+cmdstr)
            elif cmdtype=='link':
                opt, arg = getopt(cmdstr.split(' ')[1:],'',())
                if not opt and len(arg)==3 and arg[2] in ('up','down'): # link <srcID> <dstID> up|down
                    srcID=int(arg[0])
                    dstID=int(arg[1])
                    self._sib.links[(srcID,dstID)]['Active']=(arg[2].lower()=='up')
                else:
                    raise ValueError(cmdtype+' '+cmdstr)
            elif cmdtype=='traffic':
                trafficID=cmdstr.split(' ')[1]
                opt, arg = getopt(cmdstr.split(' ')[2:],'',('trafficPattern=','value=','min=','max='))
                opt = dict(opt)
                if not arg and opt['--trafficPattern']=='constant' and '--value' in opt: # traffic <trafficID> --trafficPattern constant --value <value in Mbps>:
                    self._sib.flows[trafficID]['bw']=lambda :float(opt['--value'])
                elif not arg and opt['--trafficPattern']=='uniform' and '--min' in opt and '--max' in opt: # traffic <trafficID> --trafficPattern uniform --min <value> --max <value>:
                    self._sib.flows[trafficID]['bw']=lambda :(float(opt['--min'])+(float(opt['--max'])-float(opt['--min']))*random.random())
                else:
                    raise ValueError(cmdtype+' '+cmdstr)
            else:
                objtype=cmdstr.split(' ',2)[1].lower()
                if cmdtype=='add' and objtype=='traffic':
                    trafficID=cmdstr.split(' ')[2]
                    sfciID=cmdstr.split(' ')[3]
                    opt, arg = getopt(cmdstr.split(' ')[4:],'',())
                    if not arg and 'trafficRate' in opt: # add traffic <trafficID> <sfciID> --trafficRate <value in Mbps>
                        if trafficID in self._sib.flows:
                            raise KeyError(trafficID)
                        self._sib.flows[trafficID]={'bw':(lambda :float(opt['--trafficRate'])), 'sfciID':sfciID}
                        self._sib.sfcis[sfciID]['traffics'].add(trafficID)
                elif cmdtype=='del' and objtype=='traffic':
                    trafficID=cmdstr.split(' ')[2]
                    opt, arg = getopt(cmdstr.split(' ')[3:],'',())
                    if not opt and not arg: # del traffic <trafficID>
                        sfciID=self._sib.flows[trafficID]['sfciID']
                        self._sib.sfcis[sfciID]['traffics'].remove(trafficID)
                        self._sib.flows.pop(trafficID)
            print('OK: '+cmdstr)
        except Exception as ex:
            print('FAIL: '+cmdstr)
            ExceptionProcessor(self.logger).logException(ex, "simulator command")

def get_op_input(op_input):
    op_input.join()
    try:
        while True:
            time.sleep(0.2)
            op_input.put(raw_input('> '))
            op_input.join()
    except EOFError:
        pass

if __name__ == "__main__":
    op_input=Queue()
    op_input.put('reset')
    self_location=os.path.dirname(os.path.abspath(__file__))
    try:
        initfile=open(os.path.join(self_location, 'simulator_init_TEST'),'r')
    except IOError:
        try:
            initfile=open(os.path.join(self_location, 'simulator_init'),'r')
        except IOError:
            pass
    try:
        for line in initfile:
            op_input.put(line)
    except NameError:
        pass
    thrd=threading.Thread(target=get_op_input, name='simulator input', args=(op_input,))
    thrd.setDaemon(True)
    thrd.start()
    s = Simulator(op_input)
    s.startSimulator()
