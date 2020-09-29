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

class SFFSFCIAdder(BessControlPlane):
    def __init__(self,sibms):
        super(SFFSFCIAdder, self).__init__()
        self.sibms = sibms
        self.sffSFCInitializer = SFFInitializer(self.sibms)

    def addSFCIHandler(self,cmd):
        sfc = cmd.attributes['sfc']
        sfci = cmd.attributes['sfci']
        self._checkVNFISequence(sfci.VNFISequence)
        for vnf in sfci.VNFISequence:
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
                    self._addModules(server,sfc.directions,sfci,vnfi)
                    self._addRules(server,sfci,sfc.directions,vnfi)
                    self._addLinks(server,sfc.directions,vnfi)
                    self.sibms.show()
                else:
                    continue

    def _addModules(self,server,directions,sfci,vnfi):
        VNFIID = vnfi.VNFIID
        serverID = server.getServerID()
        sibm = self.sibms.getSibm(serverID)
        serverControlIP = server.getControlNICIP()
        bessServerUrl = serverControlIP + ":10514"
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            # PMDPort0
            # PMDPort()
            vnfPMDPORT0Vdev = sibm.getVdev(VNFIID,0)
            vnfPMDPort0Name = sibm.getModuleName("PMDPort",VNFIID,0)
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
            vnfPMDPORT1Vdev = sibm.getVdev(VNFIID,1)
            vnfPMDPort1Name = sibm.getModuleName("PMDPort",VNFIID,1)
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
                vnfPMDPortName = sibm.getModuleName("PMDPort",VNFIID,
                    directionID)
                nameQueueInc = sibm.getModuleName("QueueInc",VNFIID,
                    directionID)
                argument = Any()
                argument.Pack( module_msg_pb2.QueueIncArg(port=vnfPMDPortName,
                    qid=0))
                response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                    name=nameQueueInc,mclass="QueueInc",arg=argument))
                self._checkResponse(response)

                # QueueOut()
                if directionID in [0,1]:
                    vnfPMDPortName = sibm.getModuleName("PMDPort",VNFIID,
                        1 - directionID)
                else:
                    raise ValueError('Invalid direction ID.')
                nameQueueOut = sibm.getModuleName("QueueOut",VNFIID,
                    directionID)
                argument = Any()
                argument.Pack( module_msg_pb2.QueueOutArg(port=vnfPMDPortName,
                    qid=0))
                response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                    name=nameQueueOut,mclass="QueueOut",arg=argument))
                self._checkResponse(response)

                # Update
                # nameUpdate = sibm.getModuleName("Update",VNFIID,directionID)
                # SFCIID = sfci.SFCIID
                # srcIPValue = self._sc.ip2int(server.getDatapathNICIP())
                # nextVNFID = sibm.getNextVNFID(sfci,vnfi,directionID)
                # if nextVNFID == VNF_TYPE_CLASSIFIER:
                #     egress = direction['egress']
                #     dstIPValue = self._sc.ip2int(egress.getDatapathNICIP())
                #     argument = Any()
                #     argument.Pack( module_msg_pb2.UpdateArg( fields=[
                #         {"offset":26, "size":4, "value":srcIPValue},
                #         {"offset":30, "size":4, "value":dstIPValue}
                #         ]))
                # else:
                #     dstIPValue = sibm.getUpdateValue(SFCIID,nextVNFID)
                #     argument = Any()
                #     argument.Pack( module_msg_pb2.UpdateArg( fields=[
                #         {"offset":26, "size":4, "value":srcIPValue},
                #         {"offset":31, "size":2, "value":dstIPValue}
                #         ]))
                nameUpdate = sibm.getModuleName("Update",VNFIID,directionID)
                SFCIID = sfci.SFCIID
                srcIPValue = self._sc.ip2int(server.getDatapathNICIP())
                nextVNFID = sibm.getNextVNFID(sfci,vnfi,directionID)
                dstIPValue = sibm.getUpdateValue(SFCIID,nextVNFID)
                argument = Any()
                argument.Pack( module_msg_pb2.UpdateArg( fields=[
                    {"offset":26, "size":4, "value":srcIPValue},
                    {"offset":31, "size":2, "value":dstIPValue}
                    ]))

                response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                    name=nameUpdate,mclass="Update",arg=argument))
                self._checkResponse(response)

                # Checksum()
                nameIPChecksum = sibm.getModuleName("IPChecksum",VNFIID,directionID)
                argument = Any()
                argument.Pack( module_msg_pb2.IPChecksumArg( verify=0))
                response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                    name=nameIPChecksum,mclass="IPChecksum",arg=argument))
                self._checkResponse(response)


            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

    def _addRules(self,server,sfci,directions,vnfi):
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

                oGate = sibm.assignSFFWM2OGate(VNFID,directionID)
                value = sibm.getSFFWM2MatchValue(SFCIID,VNFID,directionID)
                value = self._sc.int2Bytes(value,4)
                argument = Any()
                arg = module_msg_pb2.WildcardMatchCommandAddArg(gate=oGate,
                    values=[{"value_bin": value }],
                    masks=[{'value_bin': b'\xFF\xFF\xFF\x80'}]
                )
                argument.Pack(arg)
                response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(
                    name="wm2",cmd="add",arg=argument))
                self._checkResponse(response)

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

    def _addLinks(self,server,directions,vnfi):
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
                nameIPChecksum = sibm.getModuleName("IPChecksum",VNFIID,
                    directionID)

                # connection
                # wm2 -> nameQueueOut
                oGate = sibm.getModuleOGate("wm2",(VNFID,directionID))
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

                stub.ResumeAll(bess_msg_pb2.EmptyRequest())