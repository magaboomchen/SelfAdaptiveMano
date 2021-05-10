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
from sam.base.flow import Flow
from Queue import Queue, Empty
from getopt import getopt
import random
import threading
import os

import subprocess
predictor=subprocess.Popen(('python3','predict.py'),cwd=os.path.dirname(os.path.abspath(__file__)), stdin=subprocess.PIPE, stdout=subprocess.PIPE)

class NF:
    def __init__(self, nf, pkt, flow_count):
        assert isinstance(pkt, int)
        assert isinstance(flow_count, int)
        self.nf=NAME_OF_VNFTYPE[nf]
        self.pkt=pkt
        self.flow_count=flow_count

    def __str__(self):
        return '%s %d %d'%(self.nf, self.pkt, self.flow_count)

def predict(target, competitors):
    assert isinstance(target, NF)
    for competitor in competitors:
        assert isinstance(competitor, NF)
    predictor.stdin.write('%d'%len(competitors))
    predictor.stdin.write(str(target))
    for competitor in competitors:
        predictor.stdin.write(str(competitor))
    return float(predictor.stdout.readline())

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
        assert len(directions) in {1,2}
        assert [direction['ID'] for direction in directions]==list(len(directions))
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
        routingMorphic=sfc.routingMorphic # should not be None to generate identifierDict for Flow
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
            else:
                raise ValueError('unknown dirID')
            assert len(pathlist)==len(vnfiSequence)+1
            ingress=direction['ingress']
            ingressID=ingress.getServerID()
            egress=direction['egress']
            egressID=egress.getServerID()
            assert ingressID==pathlist[0][0][1]
            assert (pathlist[0][0][1],pathlist[0][1][1]) in self._sib.serverLinks
            assert egressID==pathlist[-1][-1][1]
            assert (pathlist[-1][-2][1],pathlist[-1][-1][1]) in self._sib.serverLinks
            for i,vnfiSeqStage in enumerate(vnfiSequence) if dirID==0 else enumerate(reversed(vnfiSequence)):
                vnfi=vnfiSeqStage[0] # no backup
                node=vnfi.node
                if isinstance(node,Server):
                    nodeID=node.getServerID()
                elif isinstance(node,Switch):
                    nodeID=node.switchID
                assert pathlist[i][-1][1]==nodeID
                assert pathlist[i+1][0][1]==nodeID
                assert pathlist[i][-2][1]==pathlist[i+1][1][1]
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

        # check and assign resources
        # server core, switch tcam, switch nextHop, (server)link usedBy
        direction=directions[0] # [d for d in directions if d['ID']==0][0]
        dirID=0
        pathlist=primaryForwardingPath[DIRECTION1_PATHID_OFFSET]
        for stage, path in enumerate(pathlist):
            if stage!=len(pathlist)-1: # dst is vnfi
                serverID=path[-1][1]
                serverInfo=self._sib.servers[serverID]
                server=serverInfo['server']
                switchID=path[-2][1]
                numaID=serverInfo['uplink2NUMA'][switchID]
                for core in server.getCoreNUMADistribution()[numaID]:
                    if core not in serverInfo['Status']['coreAssign']:
                        serverInfo['Status']['coreAssign'][core]=(sfciID, stage, vnfiSequence[stage][0].vnfType)
                        break
                else:
                    raise ValueError('no cores available on server %d socket %d', serverID, numaID)
        for direction in directions:
            dirID=direction['ID']
            if dirID==0:
                pathlist=primaryForwardingPath[DIRECTION1_PATHID_OFFSET]
            elif dirID==1:
                pathlist=primaryForwardingPath[DIRECTION2_PATHID_OFFSET]
            for stage, path in enumerate(pathlist):
                for hop, (_, switchID) in enumerate(path):
                    if hop!=0 and hop!=len(path)-1: # switchID is a switch, not server
                        switchInfo=self._sib.switches[switchID]
                        switch=switchInfo['switch']
                        if switch.tcamUsage>=switch.tcamSize:
                            raise ValueError('no tcam available on switch %d', switchID)
                        switch.tcamUsage+=1
                        switchInfo['Status']['nextHop'][(sfciID, dirID, stage, hop)]=path[hop+1][1]
                    if hop!=len(path)-1:
                        srcID=switchID
                        dstID=path[hop+1][1]
                        if hop==0: # server -> switch, switchID is server
                            linkInfo=self._sib.serverLinks[(srcID, dstID)]
                        elif hop==len(path)-2: # switch -> server
                            linkInfo=self._sib.serverLinks[(srcID, dstID)]
                        else: # switch -> switch
                            linkInfo=self._sib.links[(srcID, dstID)]
                        linkInfo['Status']['usedBy'].add((sfciID, dirID, stage, hop))
        # store information
        self._sib.sfcs[sfcUUID]={'sfc':sfc}
        self._sib.sfcis[sfciID]={'sfc':sfc, 'sfci':sfci, 'traffics':{direction['ID']:set() for direction in directions}}

    def _delSFCIHandler(self, cmd):
        sfc=cmd.attributes['sfc']
        directions=sfc.directions
        sfci=cmd.attributes['sfci']
        sfciID=sfci.sfciID
        vnfiSequence=sfci.vnfiSequence
        forwardingPathSet=sfci.forwardingPathSet
        primaryForwardingPath=forwardingPathSet.primaryForwardingPath
        # release resources
        # server core, switch tcam, switch nextHop, (server)link usedBy
        direction=directions[0] # [d for d in directions if d['ID']==0][0]
        dirID=0
        pathlist=primaryForwardingPath[DIRECTION1_PATHID_OFFSET]
        for stage, path in enumerate(pathlist):
            if stage!=len(pathlist)-1: # dst is vnfi
                serverID=path[-1][1]
                serverInfo=self._sib.servers[serverID]
                server=serverInfo['server']
                switchID=path[-2][1]
                numaID=serverInfo['uplink2NUMA'][switchID]
                for core in server.getCoreNUMADistribution()[numaID]:
                    if serverInfo['Status']['coreAssign'][core]==(sfciID, stage, vnfiSequence[stage][0].vnfType):
                        serverInfo['Status']['coreAssign'].pop(core)
                        break
                else:
                    raise ValueError('no cores to release on server %d socket %d', serverID, numaID)
        for direction in directions:
            dirID=direction['ID']
            if dirID==0:
                pathlist=primaryForwardingPath[DIRECTION1_PATHID_OFFSET]
            elif dirID==1:
                pathlist=primaryForwardingPath[DIRECTION2_PATHID_OFFSET]
            for stage, path in enumerate(pathlist):
                for hop, (_, switchID) in enumerate(path):
                    if hop!=0 and hop!=len(path)-1: # switchID is a switch, not server
                        switchInfo=self._sib.switches[switchID]
                        switch=switchInfo['switch']
                        if switch.tcamUsage<=0:
                            raise ValueError('no tcam to release on switch %d', switchID)
                        switch.tcamUsage-=1
                        switchInfo['Status']['nextHop'].pop((sfciID, dirID, stage, hop))
                    if hop!=len(path)-1:
                        srcID=switchID
                        dstID=path[hop+1][1]
                        if hop==0: # server -> switch, switchID is server
                            linkInfo=self._sib.serverLinks[(srcID, dstID)]
                        elif hop==len(path)-2: # switch -> server
                            linkInfo=self._sib.serverLinks[(srcID, dstID)]
                        else: # switch -> switch
                            linkInfo=self._sib.links[(srcID, dstID)]
                        linkInfo['Status']['usedBy'].remove((sfciID, dirID, stage, hop))
        # purge information
        for traffics in self._sib.sfcis[sfciID]['traffics'].values():
            for trafficID in traffics:
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
        for sfciID, sfciInfo in self._sib.sfcis.items():
            sfci=sfciInfo['sfci']
            assert len(sfci.vnfiSequence)==1 # can only handle single NF instances instead of chains
            sfc=sfciInfo['sfc']
            directions=sfc.directions
            traffics_by_dir=sfciInfo['traffics']

            if 0 in traffics_by_dir: # forward
                traffic_forward=list(traffics_by_dir[0])
                pathlist=sfci.forwardingPathSet.primaryForwardingPath[DIRECTION1_PATHID_OFFSET]
                path=pathlist[0]
                for i, (_, nodeID) in path:
                    if i==0 or i==len(path)-1: # ingress server and vnfi server
                        if not self._sib.servers[nodeID]['Active']:
                            traffic_forward=[]
                    else: # switch
                        if not self._sib.switches[nodeID]['Active']:
                            traffic_forward=[]
                    if i==len(path)-1:
                        pass
                    elif i==0 or i==len(path)-2: # server-switch link
                        if not self._sib.serverLinks[(nodeID, path[i+1][1])]['Active']:
                            traffic_forward=[]
                    else: # switch-switch link
                        if not self._sib.links[(nodeID, path[i+1][1])]['Active']:
                            traffic_forward=[]
            else:
                traffic_forward=[]

            if 1 in traffics_by_dir: # backward
                traffic_backward=list(traffics_by_dir[1])
                pathlist=sfci.forwardingPathSet.primaryForwardingPath[DIRECTION2_PATHID_OFFSET]
                path=pathlist[0]
                for i, (_, nodeID) in path:
                    if i==0 or i==len(path)-1: # ingress server and vnfi server
                        if not self._sib.servers[nodeID]['Active']:
                            traffic_backward=[]
                    else: # switch
                        if not self._sib.switches[nodeID]['Active']:
                            traffic_backward=[]
                    if i==len(path)-1:
                        pass
                    elif i==0 or i==len(path)-2: # server-switch link
                        if not self._sib.serverLinks[(nodeID, path[i+1][1])]['Active']:
                            traffic_backward=[]
                    else: # switch-switch link
                        if not self._sib.links[(nodeID, path[i+1][1])]['Active']:
                            traffic_backward=[]
            else:
                traffic_backward=[]

            if not traffic_forward and not traffic_backward: # no traffic on this sfci
                continue
            traffics=traffic_forward+traffic_backward
            assert len({self._sib.flows[trafficID]['pkt_size'] for trafficID in traffics})==1
            target=NF(sfci.vnfiSequence[0][0].vnfType, self._sib.flows[traffics[0]]['pkt_size'], 4000000) # no information about flow_count
            serverID=sfci.vnfiSequence[0][0].node.getServerID()
            switchID=sfci.forwardingPathSet.primaryForwardingPath[DIRECTION2_PATHID_OFFSET][0][-2][1] # last switch on path ingress->vnfi
            serverInfo=self._sib.servers[serverID]
            server=serverInfo['Server']
            competitors=[]
            for coreID in server.getCoreNUMADistribution()[serverInfo['uplink2NUMA'][switchID]]:
                if coreID in serverInfo['Status']['coreAssign'] and serverInfo['Status']['coreAssign'][coreID][:1]!=(sfciID, 0): # competitor core on the same NUMA node
                    c_sfciID=serverInfo['Status']['coreAssign'][coreID][0]
                    c_sfciInfo=self._sib.sfcis[c_sfciID]
                    c_sfci=c_sfciInfo['sfci']
                    c_sfc=c_sfciInfo['sfc']
                    c_directions=c_sfc.directions
                    c_traffics_by_dir=c_sfciInfo['traffics']
                    if 0 in c_traffics_by_dir: # forward
                        c_traffic_forward=list(c_traffics_by_dir[0])
                        c_pathlist=c_sfci.forwardingPathSet.primaryForwardingPath[DIRECTION1_PATHID_OFFSET]
                        c_path=c_pathlist[0]
                        for i, (_, nodeID) in c_path:
                            if i==0 or i==len(c_path)-1: # ingress server and vnfi server
                                if not self._sib.servers[nodeID]['Active']:
                                    c_traffic_forward=[]
                            else: # switch
                                if not self._sib.switches[nodeID]['Active']:
                                    c_traffic_forward=[]
                            if i==len(c_path)-1:
                                pass
                            elif i==0 or i==len(c_path)-2: # server-switch link
                                if not self._sib.serverLinks[(nodeID, c_path[i+1][1])]['Active']:
                                    c_traffic_forward=[]
                            else: # switch-switch link
                                if not self._sib.links[(nodeID, c_path[i+1][1])]['Active']:
                                    c_traffic_forward=[]
                    else:
                        c_traffic_forward=[]

                    if 1 in c_traffics_by_dir: # backward
                        c_traffic_backward=list(c_traffics_by_dir[1])
                        c_pathlist=c_sfci.forwardingPathSet.primaryForwardingPath[DIRECTION2_PATHID_OFFSET]
                        c_path=c_pathlist[0]
                        for i, (_, nodeID) in c_path:
                            if i==0 or i==len(c_path)-1: # ingress server and vnfi server
                                if not self._sib.servers[nodeID]['Active']:
                                    c_traffic_backward=[]
                            else: # switch
                                if not self._sib.switches[nodeID]['Active']:
                                    c_traffic_backward=[]
                            if i==len(c_path)-1:
                                pass
                            elif i==0 or i==len(c_path)-2: # server-switch link
                                if not self._sib.serverLinks[(nodeID, c_path[i+1][1])]['Active']:
                                    c_traffic_backward=[]
                            else: # switch-switch link
                                if not self._sib.links[(nodeID, c_path[i+1][1])]['Active']:
                                    c_traffic_backward=[]
                    else:
                        c_traffic_backward=[]

                    c_traffics=c_traffic_forward+c_traffic_backward
                    if c_traffics: # this competitor has traffic
                        competitors.append(NF(serverInfo['Status']['coreAssign'][coreID][2], self._sib.flows[c_traffics[0]]['pkt_size'], 4000000)) # no info about flow_count
            input_pps_list=[self._sib.flows[traffic]['bw']()*1e6/8/self._sib.flows[traffic]['pkt_size'] for traffic in traffics]
            input_pps=sum(input_pps_list)
            response_ratio=min(predict(target, competitors)/input_pps,1.0)

            identifierDict=sfc.routingMorphic.getIdentifierDict()
            identifierDict['value']=sfc.routingMorphic.encodeIdentifierForSFC(sfci.sfciID, sfci.vnfiSequence[0][0].vnfID)
            identifierDict['humanReadable']=sfc.routingMorphic.value2HumanReadable(identifierDict['value'])

            for i, trafficID in enumerate(traffic_forward):
                pps_in=input_pps_list[i]
                result.append(Flow(identifierDict, pps_in/1e6, pps_in/1e6*8*self._sib.flows[trafficID]['pkt_size']))
            for i, trafficID in enumerate(traffic_backward):
                pps_in=input_pps_list[i+len(traffic_forward)]
                result.append(Flow(identifierDict, pps_in/1e6, pps_in/1e6*8*self._sib.flows[trafficID]['pkt_size']))

            no_traffic_fw=False
            if 0 in traffics_by_dir: # forward
                pathlist=sfci.forwardingPathSet.primaryForwardingPath[DIRECTION1_PATHID_OFFSET]
                path=pathlist[1]
                for i, (_, nodeID) in path:
                    if i==0 or i==len(path)-1: # ingress server and vnfi server
                        if not self._sib.servers[nodeID]['Active']:
                            no_traffic_fw=True
                    else: # switch
                        if not self._sib.switches[nodeID]['Active']:
                            no_traffic_fw=True
                    if i==len(path)-1:
                        pass
                    elif i==0 or i==len(path)-2: # server-switch link
                        if not self._sib.serverLinks[(nodeID, path[i+1][1])]['Active']:
                            no_traffic_fw=True
                    else: # switch-switch link
                        if not self._sib.links[(nodeID, path[i+1][1])]['Active']:
                            no_traffic_fw=True
            else:
                no_traffic_fw=True

            no_traffic_bw=False
            if 1 in traffics_by_dir: # backward
                pathlist=sfci.forwardingPathSet.primaryForwardingPath[DIRECTION2_PATHID_OFFSET]
                path=pathlist[1]
                for i, (_, nodeID) in path:
                    if i==0 or i==len(path)-1: # ingress server and vnfi server
                        if not self._sib.servers[nodeID]['Active']:
                            no_traffic_bw=True
                    else: # switch
                        if not self._sib.switches[nodeID]['Active']:
                            no_traffic_bw=True
                    if i==len(path)-1:
                        pass
                    elif i==0 or i==len(path)-2: # server-switch link
                        if not self._sib.serverLinks[(nodeID, path[i+1][1])]['Active']:
                            no_traffic_bw=True
                    else: # switch-switch link
                        if not self._sib.links[(nodeID, path[i+1][1])]['Active']:
                            no_traffic_bw=True
            else:
                no_traffic_bw=True

            if not no_traffic_fw:
                for i, trafficID in enumerate(traffic_forward):
                    pps_in=input_pps_list[i]
                    result.append(Flow(identifierDict, response_ratio*pps_in/1e6, response_ratio*pps_in/1e6*8*self._sib.flows[trafficID]['pkt_size']))
            if not no_traffic_bw:
                for i, trafficID in enumerate(traffic_backward):
                    pps_in=input_pps_list[i+len(traffic_forward)]
                    result.append(Flow(identifierDict, response_ratio*pps_in/1e6, response_ratio*pps_in/1e6*8*self._sib.flows[trafficID]['pkt_size']))

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
                opt, arg = getopt(cmdstr.split(' ')[2:],'',('trafficPattern=','value=','min=','max=','pktSize='))
                opt = dict(opt)
                if not arg and '--trafficPattern' in opt and opt['--trafficPattern']=='constant' and '--value' in opt: # traffic <trafficID> --trafficPattern constant --value <value in Mbps>:
                    self._sib.flows[trafficID]['bw']=lambda :float(opt['--value'])
                elif not arg and '--trafficPattern' in opt and opt['--trafficPattern']=='uniform' and '--min' in opt and '--max' in opt: # traffic <trafficID> --trafficPattern uniform --min <value> --max <value>:
                    self._sib.flows[trafficID]['bw']=lambda :(float(opt['--min'])+(float(opt['--max'])-float(opt['--min']))*random.random())
                elif not arg and '--pktSize' in opt: # traffic <trafficID> --pktSize <value in Bytes>:
                    self._sib.flows[trafficID]['pkt_size']=int(opt['--pktSize'])
                else:
                    raise ValueError(cmdtype+' '+cmdstr)
            else:
                objtype=cmdstr.split(' ',2)[1].lower()
                if cmdtype=='add' and objtype=='traffic':
                    trafficID=cmdstr.split(' ')[2]
                    sfciID=int(cmdstr.split(' ')[3])
                    dirID=int(cmdstr.split(' ')[4])
                    opt, arg = getopt(cmdstr.split(' ')[5:],'',())
                    if not arg and 'trafficRate' in opt: # add traffic <trafficID> <sfciID> <dirID> --trafficRate <value in Mbps>
                        if trafficID in self._sib.flows:
                            raise KeyError(trafficID)
                        self._sib.flows[trafficID]={'bw':(lambda :float(opt['--trafficRate'])), 'pkt_size':500, 'sfciID':sfciID, 'dirID':dirID}
                        self._sib.sfcis[sfciID]['traffics'][dirID].add(trafficID)
                elif cmdtype=='del' and objtype=='traffic':
                    trafficID=cmdstr.split(' ')[2]
                    opt, arg = getopt(cmdstr.split(' ')[3:],'',())
                    if not opt and not arg: # del traffic <trafficID>
                        sfciID=self._sib.flows[trafficID]['sfciID']
                        dirID=self._sib.flows[trafficID]['dirID']
                        self._sib.sfcis[sfciID]['traffics'][dirID].remove(trafficID)
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
    try:
        s.startSimulator()
    except KeyboardInterrupt as e:
        predictor.terminate()
        raise e
