#!/usr/bin/python
# -*- coding: UTF-8 -*-

from __future__ import print_function
import grpc
from google.protobuf.any_pb2 import Any

import sam.serverController.builtin_pb.service_pb2 as service_pb2
import sam.serverController.builtin_pb.service_pb2_grpc as service_pb2_grpc
import sam.serverController.builtin_pb.bess_msg_pb2 as bess_msg_pb2
import sam.serverController.builtin_pb.module_msg_pb2 as module_msg_pb2
import sam.serverController.builtin_pb.ports.port_msg_pb2 as port_msg_pb2
from sam.serverController.bessControlPlane import *
from sam.serverController.sffController.sffInitializer import *
from sam.serverController.sffController.sibMaintainer import *
from sam.base.server import *

class SFFSFCIDeleter(BessControlPlane):
    def __init__(self,sibms):
        super(SFFSFCIDeleter, self).__init__()
        self.sibms = sibms

    def delSFCIHandler(self,cmd):
        sfc = cmd.attributes['sfc']
        sfci = cmd.attributes['sfci']
        self._checkVNFISequence(sfci.VNFISequence)
        for vnf in sfci.VNFISequence:
            for vnfi in vnf:
                if isinstance(vnfi.node, Server):
                    server = vnfi.node
                    serverID = server.getServerID()
                    serverControlIP = server.getControlNICIP()
                    bessServerUrl = serverControlIP + ":10514"
                    if not self.isBESSAlive(bessServerUrl):
                        self.sibms.delSibm(serverID)
                        continue
                    if not self.sibms.hasSibm(serverID):
                        continue
                    sibm = self.sibms.getSibm(serverID)
                    self._delLinks(server,sfc.directions,vnfi)
                    self._delRules(server,sfci,sfc.directions,vnfi)
                    self._delModules(server,sfc.directions,sfci,vnfi)
                    # self.sibms.show()
                else:
                    continue

    def _delLinks(self,server,directions,vnfi):
        VNFIID = vnfi.VNFIID
        VNFID = vnfi.VNFID
        serverID = server.getServerID()
        sibm = self.sibms.getSibm(serverID)
        serverControlIP = server.getControlNICIP()
        bessServerUrl = serverControlIP + ":10514"
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            for direction in directions:
                directionID = direction["ID"]

                nameQueueInc = sibm.getModuleName("QueueInc",VNFIID,
                    directionID)
                nameQueueOut = sibm.getModuleName("QueueOut",VNFIID,
                    directionID)
                nameUpdate = sibm.getModuleName("Update",VNFIID,
                    directionID)

                # connection
                # wm2 -> nameQueueOut
                oGate = sibm.getModuleOGate("wm2",(VNFID,directionID))
                response = stub.DisconnectModules(
                    bess_msg_pb2.DisconnectModulesRequest(
                    name="wm2",ogate=oGate))
                self._checkResponse(response)

                # nameQueueInc -> nameUpdate
                response = stub.DisconnectModules(
                    bess_msg_pb2.DisconnectModulesRequest(
                    name=nameQueueInc,ogate=0))
                self._checkResponse(response)

                # nameUpdate -> wm2
                response = stub.DisconnectModules(
                    bess_msg_pb2.DisconnectModulesRequest(
                    name=nameUpdate,ogate=0))
                self._checkResponse(response)

                stub.ResumeAll(bess_msg_pb2.EmptyRequest())

    def _delRules(self,server,sfci,directions,vnfi):
        SFCIID = sfci.SFCIID
        VNFIID = vnfi.VNFIID
        VNFID = vnfi.VNFID
        serverID = server.getServerID()
        sibm = self.sibms.getSibm(serverID)
        serverControlIP = server.getControlNICIP()
        bessServerUrl = serverControlIP + ":10514"
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            for direction in directions:
                directionID = direction["ID"]
                # add rule to wm2

                value = sibm.getSFFWM2MatchValue(SFCIID,VNFID,directionID)
                value = self._sc.int2Bytes(value,4)
                argument = Any()
                arg = module_msg_pb2.WildcardMatchCommandDeleteArg(
                    values=[{"value_bin": value }],
                    masks=[{'value_bin': b'\xFF\xFF\xFF\x80'}]
                )
                argument.Pack(arg)
                response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(
                    name="wm2",cmd="delete",arg=argument))
                self._checkResponse(response)
                sibm.delModuleOGate("wm2",(VNFID,directionID))

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

    def _delModules(self, server,directions,sfci,vnfi):
        VNFIID = vnfi.VNFIID
        serverID = server.getServerID()
        sibm = self.sibms.getSibm(serverID)
        serverControlIP = server.getControlNICIP()
        bessServerUrl = serverControlIP + ":10514"
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            for direction in directions:
                directionID = direction["ID"]

                # QueueInc()
                nameQueueInc = sibm.getModuleName("QueueInc",VNFIID,
                    directionID)
                response = stub.DestroyModule(
                    bess_msg_pb2.DestroyModuleRequest(
                    name=nameQueueInc))
                self._checkResponse(response)

                # QueueOut()
                nameQueueOut = sibm.getModuleName("QueueOut",VNFIID,
                    directionID)
                response = stub.DestroyModule(
                    bess_msg_pb2.DestroyModuleRequest(
                    name=nameQueueOut))
                self._checkResponse(response)

                # Update
                nameUpdate = sibm.getModuleName("Update",VNFIID,directionID)
                response = stub.DestroyModule(
                    bess_msg_pb2.DestroyModuleRequest(
                    name=nameUpdate))
                self._checkResponse(response)

            # PMDPort0
            # PMDPort()
            vnfPMDPort0Name = sibm.getModuleName("PMDPort",VNFIID,0)
            response = stub.DestroyPort(bess_msg_pb2.DestroyPortRequest(
                name=vnfPMDPort0Name))
            self._checkResponse(response)

            # PMDPort1
            # PMDPort()
            vnfPMDPort1Name = sibm.getModuleName("PMDPort",VNFIID,1)
            response = stub.DestroyPort(bess_msg_pb2.DestroyPortRequest(
                name=vnfPMDPort1Name))
            self._checkResponse(response)

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())