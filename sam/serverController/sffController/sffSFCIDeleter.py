#!/usr/bin/python
# -*- coding: UTF-8 -*-

from __future__ import print_function
import grpc
from google.protobuf.any_pb2 import Any

from sam.serverController.sffController.sfcConfig import CHAIN_TYPE_NSHOVERETH, CHAIN_TYPE_UFRR, DEFAULT_CHAIN_TYPE
import sam.serverController.builtin_pb.service_pb2_grpc as service_pb2_grpc
import sam.serverController.builtin_pb.bess_msg_pb2 as bess_msg_pb2
import sam.serverController.builtin_pb.module_msg_pb2 as module_msg_pb2
from sam.serverController.bessControlPlane import BessControlPlane

from sam.base.server import Server


class SFFSFCIDeleter(BessControlPlane):
    def __init__(self,sibms,logger):
        super(SFFSFCIDeleter, self).__init__()
        self.sibms = sibms
        self.logger = logger

    def delSFCIHandler(self,cmd):
        sfc = cmd.attributes['sfc']
        sfci = cmd.attributes['sfci']
        self._checkVNFISequence(sfci.vnfiSequence)
        self.logger.info("Deleting sfci: {0}".format(sfci.sfciID))
        self.sibms.delSFCI(sfci)
        for vnfiIdx,vnf in enumerate(sfci.vnfiSequence):
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
                    if sibm.hasReassignedVNFI(vnfi.vnfiID):
                        self._delRules(server, sfci, sfc.directions, vnfi, vnfiIdx, reassignedVNFI=True)
                    else:
                        self._delLinks(server, sfc.directions, vnfi)
                        self._delRules(server, sfci, sfc.directions, vnfi, vnfiIdx)
                        self._delModules(server, sfc.directions, sfci, vnfi, vnfiIdx)
                    self.sibms.show()
                    sibm.delVNFI(vnfi.vnfiID)
                else:
                    continue

    def _delLinks(self, server, directions, vnfi):
        vnfiID = vnfi.vnfiID
        vnfID = vnfi.vnfID
        serverID = server.getServerID()
        sibm = self.sibms.getSibm(serverID)
        serverControlIP = server.getControlNICIP()
        bessServerUrl = serverControlIP + ":10514"
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            for direction in directions:
                directionID = direction["ID"]

                nameQueueInc = sibm.getModuleName("QueueInc",vnfiID,
                    directionID)
                nameQueueOut = sibm.getModuleName("QueueOut",vnfiID,
                    directionID)
                nameUpdate = sibm.getModuleName("Update",vnfiID,
                    directionID)
                nameIPChecksum = sibm.getModuleName("IPChecksum",vnfiID,
                    directionID)

                # connection
                if DEFAULT_CHAIN_TYPE == CHAIN_TYPE_UFRR:
                    # wm2 -> nameQueueOut
                    oGate = sibm.getModuleOGate("wm2",(vnfiID,directionID))
                    response = stub.DisconnectModules(
                        bess_msg_pb2.DisconnectModulesRequest(
                        name="wm2",ogate=oGate))
                    self._checkResponse(response)

                    # nameQueueInc -> nameUpdate
                    response = stub.DisconnectModules(
                        bess_msg_pb2.DisconnectModulesRequest(
                        name=nameQueueInc,ogate=0))
                    self._checkResponse(response)

                    # nameUpdate -> IPChecksum
                    response = stub.DisconnectModules(
                        bess_msg_pb2.DisconnectModulesRequest(
                        name=nameUpdate,ogate=0))
                    self._checkResponse(response)

                    # IPChecksum -> wm2
                    response = stub.DisconnectModules(
                        bess_msg_pb2.DisconnectModulesRequest(
                        name=nameIPChecksum,ogate=0))
                    self._checkResponse(response)
                elif  DEFAULT_CHAIN_TYPE == CHAIN_TYPE_NSHOVERETH:
                    # em1 -> nameQueueOut
                    oGate = sibm.getModuleOGate("em1",(vnfiID,directionID))
                    response = stub.DisconnectModules(
                        bess_msg_pb2.DisconnectModulesRequest(
                        name="em1",ogate=oGate))
                    self._checkResponse(response)

                    # nameQueueInc -> nameUpdate
                    response = stub.DisconnectModules(
                        bess_msg_pb2.DisconnectModulesRequest(
                        name=nameQueueInc,ogate=0))
                    self._checkResponse(response)

                    # nameUpdate -> em1
                    response = stub.DisconnectModules(
                        bess_msg_pb2.DisconnectModulesRequest(
                        name=nameUpdate,ogate=0))
                    self._checkResponse(response)

                stub.ResumeAll(bess_msg_pb2.EmptyRequest())

    def _delRules(self, server, sfci, directions, vnfi, vnfiIdx, reassignedVNFI=False):
        sfciID = sfci.sfciID
        vnfiID = vnfi.vnfiID
        vnfID = vnfi.vnfID
        serverID = server.getServerID()
        sibm = self.sibms.getSibm(serverID)
        serverControlIP = server.getControlNICIP()
        bessServerUrl = serverControlIP + ":10514"
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            for direction in directions:
                directionID = direction["ID"]

                if DEFAULT_CHAIN_TYPE == CHAIN_TYPE_UFRR:
                    # del rule from wm2
                    value = sibm.getSFFWM2MatchValue(sfciID,vnfID,directionID)
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
                    if not reassignedVNFI:
                        sibm.delModuleOGate("wm2",(vnfiID,directionID))
                elif  DEFAULT_CHAIN_TYPE == CHAIN_TYPE_NSHOVERETH:
                    # del rule from em1
                    value = sibm.getSFFEM1MatchValue(sfci, vnfiIdx, directionID)
                    value = self._sc.int2Bytes(value, 4)
                    argument = Any()
                    arg = module_msg_pb2.ExactMatchCommandDeleteArg(
                        fields=[{"value_bin": value}]
                    )
                    argument.Pack(arg)
                    response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(
                        name="em1",cmd="delete",arg=argument))
                    self._checkResponse(response)
                    if not reassignedVNFI:
                        sibm.delModuleOGate("em1",(vnfiID,directionID))

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

    def _delModules(self, server, directions, sfci, vnfi, vnfiIdx):
        vnfiID = vnfi.vnfiID
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
                nameQueueInc = sibm.getModuleName("QueueInc",vnfiID,
                    directionID)
                response = stub.DestroyModule(
                    bess_msg_pb2.DestroyModuleRequest(
                    name=nameQueueInc))
                self._checkResponse(response)

                # QueueOut()
                nameQueueOut = sibm.getModuleName("QueueOut",vnfiID,
                    directionID)
                response = stub.DestroyModule(
                    bess_msg_pb2.DestroyModuleRequest(
                    name=nameQueueOut))
                self._checkResponse(response)

                # Update
                nameUpdate = sibm.getModuleName("Update",vnfiID,directionID)
                response = stub.DestroyModule(
                    bess_msg_pb2.DestroyModuleRequest(
                    name=nameUpdate))
                self._checkResponse(response)

                if DEFAULT_CHAIN_TYPE == CHAIN_TYPE_UFRR:
                    # Checksum()
                    nameIPChecksum = sibm.getModuleName("IPChecksum",vnfiID,directionID)
                    response = stub.DestroyModule(
                        bess_msg_pb2.DestroyModuleRequest(
                        name=nameIPChecksum))
                    self._checkResponse(response)

            # PMDPort0
            # PMDPort()
            vnfPMDPort0Name = sibm.getModuleName("PMDPort",vnfiID,0)
            response = stub.DestroyPort(bess_msg_pb2.DestroyPortRequest(
                name=vnfPMDPort0Name))
            self._checkResponse(response)

            # PMDPort1
            # PMDPort()
            vnfPMDPort1Name = sibm.getModuleName("PMDPort",vnfiID,1)
            response = stub.DestroyPort(bess_msg_pb2.DestroyPortRequest(
                name=vnfPMDPort1Name))
            self._checkResponse(response)

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())
