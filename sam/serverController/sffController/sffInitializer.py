#!/usr/bin/python
# -*- coding: UTF-8 -*-

from __future__ import print_function
import logging

from google.protobuf.any_pb2 import Any
import grpc

import sam.serverController.builtin_pb.service_pb2 as service_pb2
import sam.serverController.builtin_pb.service_pb2_grpc as service_pb2_grpc
import sam.serverController.builtin_pb.bess_msg_pb2 as bess_msg_pb2
import sam.serverController.builtin_pb.module_msg_pb2 as module_msg_pb2
import sam.serverController.builtin_pb.ports.port_msg_pb2 as port_msg_pb2
from sam.base.server import Server
from sam.base.messageAgent import *
from sam.base.sfc import *
from sam.base.socketConverter import SocketConverter
from sam.base.command import *
from sam.base.path import *
from sam.serverController.bessControlPlane import *


class SFFInitializer(BessControlPlane):
    def __init__(self,sibms,logger):
        super(SFFInitializer, self).__init__()
        self.sibms = sibms
        self.logger = logger

    def initClassifier(self,server):
        serverID = server.getServerID()
        self.sibms.addSibm(serverID)
        self._addModules(server)
        self._addRules(server)
        self._addLinks(server)

    def _addModules(self,server):
        serverID = server.getServerID()
        sibm = self.sibms.getSibm(serverID)
        serverControlIP = server.getControlNICIP()
        bessServerUrl = serverControlIP + ":10514"
        self.logger.info(
            "sffInitializer - bessServerUrl:{0}".format(bessServerUrl))
        if not self.isBESSAlive(bessServerUrl):
            raise ValueError ("bess is not alive")
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())
            stub.ResetAll(bess_msg_pb2.EmptyRequest())

            # NIC
            # PMDPort()
            argument = Any()
            argument.Pack( port_msg_pb2.PMDPortArg(loopback=True,port_id=0,
                vlan_offload_rx_strip=False,vlan_offload_rx_filter=False,
                vlan_offload_rx_qinq =False
                ))
            response = stub.CreatePort(bess_msg_pb2.CreatePortRequest(
                name="DatapathNICPort",driver="PMDPort",num_inc_q=1,
                num_out_q=1, size_inc_q=0, size_out_q=0, arg=argument))
            self._checkResponse(response)
            # QueueInc()
            argument = Any()
            argument.Pack( module_msg_pb2.QueueIncArg(port="DatapathNICPort",
                qid=0))
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name="input0",mclass="QueueInc",arg=argument))
            self._checkResponse(response)
            # QueueOut()
            argument = Any()
            argument.Pack( module_msg_pb2.QueueOutArg(port="DatapathNICPort",
                qid=0))
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name="output0",mclass="QueueOut",arg=argument))
            self._checkResponse(response)

            # WildcardMatch() 1
            argument = Any()
            argument.Pack(module_msg_pb2.WildcardMatchArg( fields=[
                {"offset":12, "num_bytes":2},
                {"offset":30, "num_bytes":4}
            ]))
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name="wm1",mclass="WildcardMatch",arg=argument))
            self._checkResponse(response)

            # WildcardMatch() 2
            argument = Any()
            argument.Pack( module_msg_pb2.WildcardMatchArg( fields=[
                {"offset":30, "num_bytes":4}] ))
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name="wm2",mclass="WildcardMatch",arg=argument))
            self._checkResponse(response)

            sibm.addModule("wm2","WildcardMatch")

            # ArpResponder()
            argument = Any()
            arg = module_msg_pb2.ArpResponderArg()
            argument.Pack(arg)
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name="ar",mclass="ArpResponder", arg=argument))
            self._checkResponse(response)

            # Sink()
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name="Sink1",mclass="Sink"))
            self._checkResponse(response)

            # MACSwap()
            argument = Any()
            arg = module_msg_pb2.MACSwapArg()
            argument.Pack(arg)
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name="ms",mclass="MACSwap",arg=argument))
            self._checkResponse(response)

            # Merge()
            argument = Any()
            argument.Pack( module_msg_pb2.MergeArg( ))
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name="outmerge",mclass="Merge",arg=argument))
            self._checkResponse(response)

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

    def _addRules(self,server):
        serverID = server.getServerID()
        sibm = self.sibms.getSibm(serverID)
        serverControlIP = server.getControlNICIP()
        bessServerUrl = serverControlIP + ":10514"
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            # Wildcard match
            # rule 1
            # default gate 0
            argument = Any()
            arg = module_msg_pb2.WildcardMatchCommandSetDefaultGateArg(gate=0)
            argument.Pack(arg)
            response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(
                name="wm1",cmd="set_default_gate",arg=argument))
            self._checkResponse(response)
            # rule 2
            # sfc domain traffic to gate 1
            argument = Any()
            dstIPMask = self._sc.ipPrefix2Mask(SFC_DOMAIN_PREFIX_LENGTH)
            dstIPMask = self._sc.aton(dstIPMask)
            arg = module_msg_pb2.WildcardMatchCommandAddArg(gate=1,
                values=[
                    {"value_bin": b'\x08\x00'},
                    {"value_bin":self._sc.aton(SFC_DOMAIN_PREFIX)}
                ],
                masks=[
                    {'value_bin': b'\xFF\xFF'},
                    {'value_bin':dstIPMask}
                ])
            argument.Pack(arg)
            response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(
                name="wm1",cmd="add",arg=argument))
            # rule 3
            # arp traffic to gate 2
            argument = Any()
            arg = module_msg_pb2.WildcardMatchCommandAddArg(gate=2,
                values=[
                    {"value_bin": b'\x08\x06'},
                    {"value_bin": b'\x00\x00\x00\x00'}
                ],
                masks=[
                    {'value_bin': b'\xFF\xFF'},
                    {'value_bin': b'\x00\x00\x00\x00'}
                ])
            argument.Pack(arg)
            response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(
                name="wm1",cmd="add",arg=argument))
            self._checkResponse(response)

            # WildcardMatch
            # rule 1
            # wm2.set_default_gate(gate=0)
            argument = Any()
            argument.Pack( module_msg_pb2.WildcardMatchCommandSetDefaultGateArg(
                gate=0) )
            response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(
                name="wm2",cmd="set_default_gate",arg=argument))
            self._checkResponse(response)

            sibm.addOGate2Module("wm2","default",0)

            # add rule to ArpResponder
            serverDatapathNICIP = server.getDatapathNICIP()
            serverControlNICMAC = server.getDatapathNICMac()
            self.logger.debug("ArpResponder IP:{}, MAC:{}".format(
                serverDatapathNICIP,serverControlNICMAC))
            argument = Any()
            arg = module_msg_pb2.ArpResponderArg(ip=serverDatapathNICIP,
                mac_addr=serverControlNICMAC)
            argument.Pack(arg)
            response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(
                    name="ar",cmd="add",arg=argument))
            self._checkResponse(response)

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

    def _addLinks(self,server):
        serverControlIP = server.getControlNICIP()
        bessServerUrl = serverControlIP + ":10514"
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            # Connection
            # input0 -> wm
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1="input0",m2="wm1",ogate=0,igate=0))
            self._checkResponse(response)

            # wm:0 -> Sink()
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1="wm1",m2="Sink1",ogate=0,igate=0))
            self._checkResponse(response)

            # wm:1 -> WildcardMatch()
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1="wm1",m2="wm2",ogate=1,igate=0))
            self._checkResponse(response)

            # wm:2 -> ar
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1="wm1",m2="ar",ogate=2,igate=0))
            self._checkResponse(response)

            #   ar-> outmerge
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1="ar",m2="outmerge",ogate=0,igate=0))
            self._checkResponse(response)

            # wm2:0 -> ms
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1="wm2",m2="ms",ogate=0,igate=0))
            self._checkResponse(response)

            #       ms -> outmerge
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1="ms",m2="outmerge",ogate=0,igate=0))
            self._checkResponse(response)

            # outmerge -> output0
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1="outmerge",m2="output0",ogate=0,igate=0))
            self._checkResponse(response)

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())