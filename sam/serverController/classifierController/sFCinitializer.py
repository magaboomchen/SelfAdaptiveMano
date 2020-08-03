#!/usr/bin/env python
from __future__ import print_function
import grpc
import os
from google.protobuf.any_pb2 import Any
import pika
import base64
import pickle
import time
import uuid
import subprocess
import logging
import Queue
import struct

import sam.serverController.builtin_pb.service_pb2 as service_pb2
import sam.serverController.builtin_pb.service_pb2_grpc as service_pb2_grpc
import sam.serverController.builtin_pb.bess_msg_pb2 as bess_msg_pb2
import sam.serverController.builtin_pb.module_msg_pb2 as module_msg_pb2
import sam.serverController.builtin_pb.ports.port_msg_pb2 as port_msg_pb2

from sam.base.server import Server
from sam.base.messageAgent import *
from sam.base.sfc import *
from sam.base.socketConverter import SocketConverter
from sam.base.socketConverter import SocketConverter as SC
from sam.base.command import *
from sam.base.path import *
from sam.serverController.bessGRPC import *

class ClassifierInitializer(BessGRPC):
    def __init__(self,clsMaintainer):
        self.clsMaintainer = clsMaintainer
        self._classifierSet = {} # TODO replace
        self._commands = {} # TODO replace
        self._sc = SocketConverter() # TODO replace

    def initClassifier(self,cmd):
        classifier = cmd.attributes['classifier']
        serverID = classifier.getServerID()
        if not serverID in self._classifierSet.iterkeys():
            self._classifierSet[serverID] = {"server":classifier,"sfcSet":{}}
            self._initAddModules(classifier)
            self._initAddRules(classifier)
            self._initAddLinks(classifier)

    def _initAddModules(self,classifier):
        bessServerUrl = classifier.getControlNICIP() + ":10514"
        logging.info(bessServerUrl)
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())
            stub.ResetAll(bess_msg_pb2.EmptyRequest())

            # NICs
            # PMDPort()
            argument = Any()
            arg = port_msg_pb2.PMDPortArg(loopback=True,port_id=0,
                vlan_offload_rx_strip=False,vlan_offload_rx_filter=False,
                vlan_offload_rx_qinq =False)
            argument.Pack(arg)
            response = stub.CreatePort(bess_msg_pb2.CreatePortRequest(
                name="DatapathNICPort",driver="PMDPort",num_inc_q=1,
                num_out_q=1, size_inc_q=0, size_out_q=0, arg=argument))
            self._checkResponse(response)
            # QueueInc()
            argument = Any()
            arg = module_msg_pb2.QueueIncArg(port="DatapathNICPort", qid=0)
            argument.Pack(arg)
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name="input0",mclass="QueueInc",arg=argument))
            self._checkResponse(response)
            # QueueOut()
            argument = Any()
            arg = module_msg_pb2.QueueOutArg(port="DatapathNICPort", qid=0)
            argument.Pack(arg)
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name="output0",mclass="QueueOut",arg=argument))
            self._checkResponse(response)

            # Setmetadata()
            argument = Any()
            arg = module_msg_pb2.SetMetadataArg(attrs=[
                {'name':"src_mac", 'size':6, 'offset':0},
                {'name':"dst_mac", 'size':6, 'offset':6}
            ])
            argument.Pack(arg)
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name="setmetadata",mclass="SetMetadata",arg=argument))
            self._checkResponse(response)

            # WildcardMatch1()
            argument = Any()
            arg = module_msg_pb2.WildcardMatchArg(fields=[
                {"offset":12, "num_bytes":2}])
            argument.Pack(arg)
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name="wm1",mclass="WildcardMatch",arg=argument))
            self._checkResponse(response)

            # TODO: MACSwap()

            # WildcardMatch2()
            argument = Any()
            arg = module_msg_pb2.WildcardMatchArg( 
                fields=[{"offset":23, "num_bytes":1},
                {"offset":26, "num_bytes":4},
                {"offset":30, "num_bytes":4},
                {"offset":34, "num_bytes":2},
                {"offset":36, "num_bytes":2}]
                )
            argument.Pack(arg)
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name="wm2",mclass="WildcardMatch",arg=argument))
            self._checkResponse(response)

            # ArpResponder()
            argument = Any()
            arg = module_msg_pb2.ArpResponderArg()
            argument.Pack(arg)
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name="ar",mclass="ArpResponder", arg=argument))
            self._checkResponse(response)

            # EtherEncap()
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name="ee",mclass="EtherEncap"))
            self._checkResponse(response)

            # GenericDecap()
            argument = Any()
            arg = module_msg_pb2.GenericDecapArg(bytes=34)
            argument.Pack(arg)
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name="gdInit",mclass="GenericDecap",arg=argument))
            self._checkResponse(response)

            # Merge
            # outmerge::Merge() -> output0
            argument = Any()
            arg = module_msg_pb2.MergeArg()
            argument.Pack(arg)
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name="outmerge",mclass="Merge",arg=argument))
            self._checkResponse(response)

            # Sink
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name="Sink1",mclass="Sink"))
            self._checkResponse(response)

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

            # list all module
            response = stub.ListModules(bess_msg_pb2.EmptyRequest())
            if response.error.code != 0:
                logging.error( str(response.error) )
                raise ValueError('bess cmd failed.')
            else:
                for m in response.modules:
                    logging.info(' {0},{1},{2}'.format(m.name,m.mclass,m.desc))

    def _initAddRules(self,classifier):
        bessServerUrl = classifier.getControlNICIP() + ":10514"
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            # add rule to wm1
            # rule 1
            # default gate 0
            argument = Any()
            arg = module_msg_pb2.WildcardMatchCommandSetDefaultGateArg(gate=0)
            argument.Pack(arg)
            response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(
                name="wm1",cmd="set_default_gate",arg=argument))
            self._checkResponse(response)

            # rule 2
            # ipv4 traffic to gate 1
            argument = Any()
            arg = module_msg_pb2.WildcardMatchCommandAddArg(gate=1,
                values=[{"value_bin": b'\x08\x00' }],
                masks=[{'value_bin': b'\xFF\xFF'}])
            argument.Pack(arg)
            response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(
                name="wm1",cmd="add",arg=argument))
            self._checkResponse(response)

            # rule 3
            # apr traffic to gate 2
            argument = Any()
            arg = module_msg_pb2.WildcardMatchCommandAddArg(gate=2,
                values=[{"value_bin": b'\x08\x06'}],
                masks=[{'value_bin': b'\xFF\xFF'}])
            argument.Pack(arg)
            response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(
                name="wm1",cmd="add",arg=argument))
            self._checkResponse(response)

            # add rule to ArpResponder
            classifierIP = classifier.getDatapathNICIP()
            classifierMAC = classifier.getDatapathNICMac()
            logging.debug("ArpResponder IP:{}, MAC:{}".format(classifierIP,
                classifierMAC))
            argument = Any()
            arg = module_msg_pb2.ArpResponderArg(ip=classifierIP,
                mac_addr=classifierMAC)
            argument.Pack(arg)
            response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(
                    name="ar",cmd="add",arg=argument))
            self._checkResponse(response)

            # add rule to wm2
            # rule 1
            # default gate 0
            argument = Any()
            arg = module_msg_pb2.WildcardMatchCommandSetDefaultGateArg(gate=0)
            argument.Pack(arg)
            response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(
                name="wm2",cmd="set_default_gate",arg=argument))
            self._checkResponse(response)
            # rule 2
            # ipv4 traffic to gate 1
            argument = Any()
            dstIPMask = self._sc.ipPrefix2Mask(32)
            dstIPMask = self._sc.aton(dstIPMask)
            classifierDatapathIP = classifier.getDatapathNICIP()
            arg = module_msg_pb2.WildcardMatchCommandAddArg(gate=1,
                values=[
                    {"value_bin":b'\x00'},
                    {"value_bin":b'\x00\x00\x00\x00\x00\x00\x00\x00'},
                    {"value_bin":self._sc.aton(classifierDatapathIP)},
                    {"value_bin":b'\x00\x00'},
                    {"value_bin":b'\x00\x00'}
                ],
                masks=[
                    {'value_bin':b'\x00'},
                    {'value_bin':b'\x00\x00\x00\x00\x00\x00\x00\x00'},
                    {'value_bin':b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF'},
                    {'value_bin':b'\x00\x00'},
                    {'value_bin':b'\x00\x00'}
                ]
                )
            argument.Pack(arg)
            response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(
                name="wm2",cmd="add",arg=argument))
            self._checkResponse(response)

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

    def _initAddLinks(self,classifier):
        bessServerUrl = classifier.getControlNICIP() + ":10514"
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            # Connection
            # input0 -> setmetadata
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1="input0",m2="setmetadata",ogate=0,igate=0))
            self._checkResponse(response)

            # setmetadata -> wm1
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1="setmetadata",m2="wm1",ogate=0,igate=0))
            self._checkResponse(response)

            # wm1:0 -> Sink1
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1="wm1",m2="Sink1",ogate=0,igate=0))
            self._checkResponse(response)

            # wm1:1 -> wm2
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1="wm1",m2="wm2",ogate=1,igate=0))
            self._checkResponse(response)

            #   wm2:0 -> Sink1
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1="wm2",m2="Sink1",ogate=0,igate=0))
            self._checkResponse(response)

            #   wm2:1 -> gdInit
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1="wm2",m2="gdInit",ogate=1,igate=0))
            self._checkResponse(response)

            #       gdInit -> ee
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1="gdInit",m2="ee",ogate=0,igate=0))
            self._checkResponse(response)

            #       ee -> outmerge
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1="ee",m2="outmerge",ogate=0,igate=0))
            self._checkResponse(response)

            # wm1:2 -> ar
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1="wm1",m2="ar",ogate=2,igate=0))
            self._checkResponse(response)

            #   ar-> outmerge
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1="ar",m2="outmerge",ogate=0,igate=0))
            self._checkResponse(response)

            # outmerge -> output0
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1="outmerge",m2="output0",ogate=0,igate=0))
            self._checkResponse(response)

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())