#!/usr/bin/python
# -*- coding: UTF-8 -*-

from __future__ import print_function
import math
import grpc
from google.protobuf.any_pb2 import Any

from sam.base.server import Server
from sam.serverController.sffController.sfcConfig import CHAIN_TYPE_NSHOVERETH, CHAIN_TYPE_UFRR, DEFAULT_CHAIN_TYPE
import sam.serverController.builtin_pb.service_pb2_grpc as service_pb2_grpc
import sam.serverController.builtin_pb.bess_msg_pb2 as bess_msg_pb2
import sam.serverController.builtin_pb.module_msg_pb2 as module_msg_pb2
import sam.serverController.builtin_pb.ports.port_msg_pb2 as port_msg_pb2
from sam.serverController.bessControlPlane import BessControlPlane
from sam.serverController.sffController.sffInitializer import SFFInitializer


class SFFSFCIAdder(BessControlPlane):
    def __init__(self,sibms, logger):
        super(SFFSFCIAdder, self).__init__()
        self.sibms = sibms
        self.logger = logger
        self.sffSFCInitializer = SFFInitializer(self.sibms, self.logger)

    def addSFCIHandler(self,cmd):
        sfc = cmd.attributes['sfc']
        sfci = cmd.attributes['sfci']
        self._checkVNFISequence(sfci.vnfiSequence)
        self.logger.info("Adding sfci: {0}".format(sfci.sfciID))
        self.sibms.addSFCI(sfci)
        for vnfiIdx,vnf in enumerate(sfci.vnfiSequence):
            for vnfi in vnf:
                if isinstance(vnfi.node, Server):
                    server = vnfi.node
                    serverControlIP = server.getControlNICIP()
                    serverID = server.getServerID()
                    bessServerUrl = serverControlIP + ":10514"
                    if not self.isBESSAlive(bessServerUrl):
                        self.sibms.delSibm(serverID)
                    if not self.sibms.hasSibm(serverID):
                        self.sffSFCInitializer.initClassifier(server)
                    sibm = self.sibms.getSibm(serverID)
                    if sibm.hasVNFI(vnfi.vnfiID):
                        # reassign sfci to an existed vnfi
                        # don't need add new modules and links
                        self.logger.warning("reassign an existed vnfi")
                        self._addRules(server, sfci, sfc.directions, vnfi, vnfiIdx)
                    else:
                        self._addModules(server, sfc.directions, sfci, vnfi, vnfiIdx)
                        self._addRules(server, sfci, sfc.directions, vnfi, vnfiIdx)
                        self._addLinks(server, sfc.directions, vnfi)
                    self.sibms.show()
                    sibm.addVNFI(vnfi)
                else:
                    continue

    def _addModules(self, server, directions, sfci, vnfi, vnfiIdx):
        vnfiID = vnfi.vnfiID
        serverID = server.getServerID()
        sibm = self.sibms.getSibm(serverID)
        serverControlIP = server.getControlNICIP()
        bessServerUrl = serverControlIP + ":10514"
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            # PMDPort0
            # PMDPort()
            vnfPMDPORT0Vdev = sibm.getVdev(vnfiID,0)
            vnfPMDPort0Name = sibm.getModuleName("PMDPort",vnfiID,0)
            argument = Any()
            argument.Pack(port_msg_pb2.PMDPortArg(loopback=True,
                vdev=vnfPMDPORT0Vdev,vlan_offload_rx_strip=False,
                vlan_offload_rx_filter=False,vlan_offload_rx_qinq =False))
            response = stub.CreatePort(bess_msg_pb2.CreatePortRequest(
                name=vnfPMDPort0Name,driver="PMDPort",num_inc_q=1,
                num_out_q=1, size_inc_q=0, size_out_q=0,arg=argument))
            self._checkResponse(response)

            # PMDPort1
            # PMDPort()
            vnfPMDPORT1Vdev = sibm.getVdev(vnfiID,1)
            vnfPMDPort1Name = sibm.getModuleName("PMDPort",vnfiID,1)
            argument = Any()
            argument.Pack(port_msg_pb2.PMDPortArg(loopback=True,
                vdev=vnfPMDPORT1Vdev,vlan_offload_rx_strip=False,
                vlan_offload_rx_filter=False,vlan_offload_rx_qinq =False))
            response = stub.CreatePort(bess_msg_pb2.CreatePortRequest(
                name=vnfPMDPort1Name,driver="PMDPort",num_inc_q=1,
                num_out_q=1, size_inc_q=0, size_out_q=0, arg=argument))
            self._checkResponse(response)

            for direction in directions:
                directionID = direction["ID"]

                # QueueInc()
                if directionID in [0,1]:
                    vnfPMDPortName = sibm.getModuleName("PMDPort",vnfiID,
                        1 - directionID)
                else:
                    raise ValueError('Invalid direction ID.')
                nameQueueInc = sibm.getModuleName("QueueInc",vnfiID,
                    directionID)
                argument = Any()
                argument.Pack( module_msg_pb2.QueueIncArg(port=vnfPMDPortName,
                    qid=0))
                response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                    name=nameQueueInc,mclass="QueueInc",arg=argument))
                self._checkResponse(response)

                # QueueOut()
                if directionID in [0,1]:
                    vnfPMDPortName = sibm.getModuleName("PMDPort",vnfiID,
                        directionID)
                else:
                    raise ValueError('Invalid direction ID.')
                nameQueueOut = sibm.getModuleName("QueueOut",vnfiID,
                    directionID)
                argument = Any()
                argument.Pack( module_msg_pb2.QueueOutArg(port=vnfPMDPortName,
                    qid=0))
                response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                    name=nameQueueOut,mclass="QueueOut",arg=argument))
                self._checkResponse(response)

                # Update sfc datapath embedding
                nameUpdate = sibm.getModuleName("Update",vnfiID,directionID)
                if DEFAULT_CHAIN_TYPE == CHAIN_TYPE_UFRR:
                    sfciID = sfci.sfciID
                    srcIPValue = self._sc.ip2int(server.getDatapathNICIP())
                    nextVNFID = sibm.getNextVNFID(sfci, vnfi, directionID)
                    dstIPValue = sibm.getUpdateValue(sfciID, nextVNFID)
                    dstIPValue = (dstIPValue >> 8) & 0xFF
                    argument = Any()
                    # Here is a bug: sfciID can't larger than 255
                    # To debug, please refactor Update.cc/.h module and module_msg.proto in bess.
                    # In details, add "value_mask" in UpdateArg()
                    # https://github.com/NetSys/bess/wiki/Writing-Your-Own-Module
                    # https://github.com/NetSys/bess/blob/ae52fc5804290fc3116daf2aef52226fafcedf5d/core/modules/update.cc
                    argument.Pack( module_msg_pb2.UpdateArg( fields=[
                        {"offset":26, "size":4, "value":srcIPValue},
                        {"offset":31, "size":1, "value":dstIPValue}
                        ]))
                elif  DEFAULT_CHAIN_TYPE == CHAIN_TYPE_NSHOVERETH:
                    value = sibm.getUpdateValue4NSH(sfci, directionID, vnfiIdx)
                    argument = Any()
                    argument.Pack( module_msg_pb2.UpdateArg( fields=[
                        {"offset":18, "size":4, "value": value}
                        ]))
                response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                    name=nameUpdate,mclass="Update",arg=argument))
                self._checkResponse(response)

                if DEFAULT_CHAIN_TYPE == CHAIN_TYPE_UFRR:
                    # Checksum()
                    nameIPChecksum = sibm.getModuleName("IPChecksum",vnfiID,directionID)
                    argument = Any()
                    argument.Pack( module_msg_pb2.IPChecksumArg( verify=0))
                    response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                        name=nameIPChecksum,mclass="IPChecksum",arg=argument))
                    self._checkResponse(response)

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

    def _addRules(self, server, sfci, directions, vnfi, vnfiIdx):
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
                    # add rule to wm2
                    oGate = sibm.assignSFFWM2OGate(vnfiID, directionID)
                    value = sibm.getSFFWM2MatchValue(sfciID, vnfID, directionID)
                    value = self._sc.int2Bytes(value, 4)
                    argument = Any()
                    arg = module_msg_pb2.WildcardMatchCommandAddArg(gate=oGate,
                        values=[{"value_bin": value }],
                        masks=[{'value_bin': b'\xFF\xFF\xFF\x80'}]
                    )
                    argument.Pack(arg)
                    response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(
                        name="wm2",cmd="add",arg=argument))
                    self._checkResponse(response)
                elif  DEFAULT_CHAIN_TYPE == CHAIN_TYPE_NSHOVERETH:
                    # add rule to em1
                    oGate = sibm.assignSFFEM1OGate(vnfiID, directionID)
                    value = sibm.getSFFEM1MatchValue(sfci, vnfiIdx, directionID)
                    value = self._sc.int2Bytes(value, 4)
                    argument = Any()
                    arg = module_msg_pb2.ExactMatchCommandAddArg(
                        gate=oGate,
                        fields=[{"value_bin": value}]
                    )
                    argument.Pack(arg)
                    response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(
                        name="em1",cmd="add",arg=argument))
                    self._checkResponse(response)

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

    def _addLinks(self,server,directions,vnfi):
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
                    response = stub.ConnectModules(
                        bess_msg_pb2.ConnectModulesRequest(
                        m1="wm2",m2=nameQueueOut,ogate=oGate,igate=0))
                    self._checkResponse(response)

                    # nameQueueInc -> nameUpdate
                    response = stub.ConnectModules(
                        bess_msg_pb2.ConnectModulesRequest(
                        m1=nameQueueInc,m2=nameUpdate,ogate=0,igate=0))
                    self._checkResponse(response)

                    # nameUpdate -> IPChecksum
                    response = stub.ConnectModules(
                        bess_msg_pb2.ConnectModulesRequest(
                        m1=nameUpdate,m2=nameIPChecksum,ogate=0,igate=0))
                    self._checkResponse(response)

                    # IPChecksum -> wm2
                    response = stub.ConnectModules(
                        bess_msg_pb2.ConnectModulesRequest(
                        m1=nameIPChecksum,m2="wm2",ogate=0,igate=0))
                    self._checkResponse(response)
                elif  DEFAULT_CHAIN_TYPE == CHAIN_TYPE_NSHOVERETH:
                    # em1 -> nameQueueOut
                    oGate = sibm.getModuleOGate("em1",(vnfiID,directionID))
                    response = stub.ConnectModules(
                        bess_msg_pb2.ConnectModulesRequest(
                        m1="em1",m2=nameQueueOut,ogate=oGate,igate=0))
                    self._checkResponse(response)

                    # nameQueueInc -> nameUpdate
                    response = stub.ConnectModules(
                        bess_msg_pb2.ConnectModulesRequest(
                        m1=nameQueueInc,m2=nameUpdate,ogate=0,igate=0))
                    self._checkResponse(response)

                    # nameUpdate -> em1
                    response = stub.ConnectModules(
                        bess_msg_pb2.ConnectModulesRequest(
                        m1=nameUpdate,m2="em1",ogate=0,igate=0))
                    self._checkResponse(response)

                stub.ResumeAll(bess_msg_pb2.EmptyRequest())