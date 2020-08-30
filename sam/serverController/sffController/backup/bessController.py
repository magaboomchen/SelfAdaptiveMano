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

import sam.serverController.builtin_pb.service_pb2
import sam.serverController.builtin_pb.service_pb2_grpc
import sam.serverController.builtin_pb.bess_msg_pb2
import sam.serverController.builtin_pb.module_msg_pb2
import sam.serverController.builtin_pb.ports.port_msg_pb2 as port_msg_pb2

from sam.base.server import Server
from sam.base.messageAgent import *
from sam.base.sfc import *
from sam.base.socketConverter import SocketConverter
from sam.orchestrator import *

class BESSState(object):
    def __init__(self):
        self.exactMatchState = {} # {"match dst ip":port}
        self.deployedVNFs = {} # {"VNF.UUID":{$SFCID:True, $SFCID:True} }

class BESSController(object):
    def __init__(self):
        logging.info("Init BESS controller.")
        self._serverSet = {}
        self._commandsInfo = {}
        self._messageAgent = MessageAgent()
        self._messageAgent.startRecvMsg(SFF_CONTROLLER_QUEUE)
        self._sc = SocketConverter()

    def startBESSController(self):
        while True:
            msg = self._messageAgent.getMsg(SFF_CONTROLLER_QUEUE)
            if msg.getMessageType() == MSG_TYPE_SSF_CONTROLLER_CMD:
                logging.info("BESS controller get a bess cmd.")
                try:
                    cmd = msg.getbody()
                    self._commandsInfo[cmd.cmdID] = {"cmd":cmd,
                        "state":CMD_STATE_PROCESSING}
                    if cmd.cmdType == CMD_TYPE_ADD_SFCI:
                        self._addSFCinBESS(cmd)
                    elif cmd.cmdType == CMD_TYPE_DEL_SFCI:
                        self._delSFCinBESS(cmd)
                    elif cmd.cmdType == CMD_TYPE_GET_VNFI_STATUS:
                        self._getVNFIStatus(cmd)
                    else:
                        logging.error("Unkonwn bess command type.")
                    self._commandsInfo[cmd.cmdID]["state"] = CMD_STATE_SUCCESSFUL
                except ValueError as err:
                    logging.error('bess cmd processing error: ' + repr(err))
                    self._commandsInfo[cmd.cmdID]["state"] = CMD_STATE_FAIL
                finally:
                    rplyMsg = SAMMessage(MSG_TYPE_SSF_CONTROLLER_CMD_REPLY,
                        CommandReply(cmd.cmdID,
                        self._commandsInfo[cmd.cmdID]["state"]) )
                    self._messageAgent.sendMsg(ORCHESTRATION_QUEUE,
                        rplyMsg)
            elif msg.getMessageType() == None:
                pass
            else:
                logging.error("Unknown msg type.")

    def _addSFCinBESS(self,cmd):
        sfc = cmd.attributes['sfc']
        for vnfiList in sfc.VNFISeq:
            for vnfi in vnfiList:
                # init new server
                if not vnfi.serverControlNICIP in self._serverSet:
                    self._initBESS(vnfi.serverControlNICIP + ":10514")
                    self._serverSet[vnfi.serverControlNICIP] = {
                        "Mac":vnfi.serverControlNICMAC,"BessState":BESSState()}
                # add rules in exactmatch
                self._addDataPathRule(vnfi.serverControlNICIP + ":10514",vnfi)
                # add VNF PMDPort
                index = sfc.VNFISeq.index(vnfiList)
                nextVNFID = -1
                if index < len(sfc.VNFISeq)-1:
                    nextVNFID = sfc.VNFISeq[index+1][0].VNFID
                self._addVNFDataPath(vnfi.serverControlNICIP + ":10514",
                    vnfi,sfc.SFCID,nextVNFID)

    def _initBESS(self,bessServerUrl):
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

            # WildcardMatch()
            argument = Any()
            argument.Pack( module_msg_pb2.WildcardMatchArg( fields=[
                {"offset":30, "num_bytes":4}] ))
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name="wm",mclass="WildcardMatch",arg=argument))
            self._checkResponse(response)
            # rule 1
            # default gate 0
            argument = Any()
            arg = module_msg_pb2.WildcardMatchCommandSetDefaultGateArg(gate=0)
            argument.Pack(arg)
            response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(
                name="wm",cmd="set_default_gate",arg=argument))
            self._checkResponse(response)
            # rule 2
            # sfc domain traffic to gate 1
            argument = Any()
            dstIPMask = self._sc.ipPrefix2Mask(SFC_DOMAIN_PREFIX_LENGTH)
            dstIPMask = self._sc.aton(dstIPMask)
            arg = module_msg_pb2.WildcardMatchCommandAddArg(gate=1,
                values=[{"value_bin":self._sc.aton(SFC_DOMAIN_PREFIX)}],
                masks=[{'value_bin':dstIPMask}])
            argument.Pack(arg)
            response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(
                name="wm",cmd="add",arg=argument))

            # EXACT MATCH
            # ExactMatch()
            argument = Any()
            argument.Pack( module_msg_pb2.ExactMatchArg( fields=[
                {"offset":30, "num_bytes":4}] ))
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name="em",mclass="ExactMatch",arg=argument))
            self._checkResponse(response)
            # rule 1
            # em.set_default_gate(gate=0)
            argument = Any()
            argument.Pack( module_msg_pb2.ExactMatchCommandSetDefaultGateArg(
                gate=0) )
            response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(
                name="em",cmd="set_default_gate",arg=argument))
            self._checkResponse(response)

            # Merge
            # outmerge::Merge() -> output0
            argument = Any()
            argument.Pack( module_msg_pb2.MergeArg( ))
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name="outmerge",mclass="Merge",arg=argument))
            self._checkResponse(response)

            # Sink
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name="Sink1",mclass="Sink"))
            self._checkResponse(response)

            # Connection
            # input0 -> wm
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1="input0",m2="wm",ogate=0,igate=0))
            self._checkResponse(response)

            # wm:0 -> Sink()
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1="wm",m2="Sink1",ogate=0,igate=0))
            self._checkResponse(response)

            # wm:1 -> ExactMatch()
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1="wm",m2="em",ogate=1,igate=0))
            self._checkResponse(response)

            # em:0 -> outmerge
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1="em",m2="outmerge",ogate=0,igate=0))
            self._checkResponse(response)

            # outmerge -> output0
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1="outmerge",m2="output0",ogate=0,igate=0))
            self._checkResponse(response)

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

    def _checkResponse(self,response):
        if response.error.code != 0:
            logging.error( str(response.error) )
            raise ValueError('bess cmd failed.')

    def _addDataPathRule(self,bessServerUrl,vnfi):
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            # add rule to em
            argument = Any()
            bessServerIP = bessServerUrl.split(":")[0]
            gatePort = self._getAvailableEmPort(
                self._serverSet[bessServerIP]["BessState"] )
            for ip in vnfi.serverDatapathNICIP:
                logging.debug("sffController.serverSet.bessState.ExactMatch.matchfield = ip:%s, gatePort:%d." %(ip, gatePort) )
                argument.Pack( module_msg_pb2.ExactMatchCommandAddArg(
                    gate=gatePort, fields=[
                        {"value_bin":self._sc.aton(ip)}] ) )
                response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(
                    name="em",cmd="add",arg=argument))
                self._checkResponse(response)
                self._serverSet[bessServerIP]["BessState"].exactMatchState[ip] = gatePort

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

    def _getAvailableEmPort( self, bessState ):
        portList = []
        for port in bessState.exactMatchState.itervalues():
            portList.append(port)
        if portList == []:
            return 1
        for i in range(1,max(portList)+2):
            if not i in portList:
                return i

    def getVdevOfVNFOutputPMDPort(self,VNFIID):
        return  "net_vhost0_" + str(VNFIID) +",iface=/tmp/vsock0_" + str(VNFIID)

    def getVdevOfVNFInputPMDPort(self,VNFIID):
        return "net_vhost1_" + str(VNFIID) +",iface=/tmp/vsock1_" + str(VNFIID)

    def _getNameOfVNFOutputPMDPort(self,VNFIID):
        return "vhost0_" + str(VNFIID)

    def _getNameOfVNFInputPMDPort(self,VNFIID):
        return "vhost1_" + str(VNFIID)

    def _addVNFDataPath(self,bessServerUrl,vnfi,SFCID,nextVNFID):
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            # PMDPort
            # PMDPort()
            vdevVNFPMDPORT0 = self.getVdevOfVNFOutputPMDPort(vnfi.VNFIID)
            nameVNFPMDPort0 = self._getNameOfVNFOutputPMDPort(vnfi.VNFIID)
            argument = Any()
            argument.Pack(port_msg_pb2.PMDPortArg(loopback=True,
                vdev=vdevVNFPMDPORT0,vlan_offload_rx_strip=False,
                vlan_offload_rx_filter=False,vlan_offload_rx_qinq =False))
            response = stub.CreatePort(bess_msg_pb2.CreatePortRequest(
                name=nameVNFPMDPort0,driver="PMDPort",num_inc_q=1,
                num_out_q=1, size_inc_q=0, size_out_q=0,arg=argument))
            self._checkResponse(response)
            # PMDPort()
            vdevVNFPMDPORT1 = self._getVdevOfVNFInputPMDPort(vnfi.VNFIID)
            nameVNFPMDPort1 = self._getNameOfVNFInputPMDPort(vnfi.VNFIID)
            argument = Any()
            argument.Pack(port_msg_pb2.PMDPortArg(loopback=True,
                vdev=vdevVNFPMDPORT1,vlan_offload_rx_strip=False,
                vlan_offload_rx_filter=False,vlan_offload_rx_qinq =False))
            response = stub.CreatePort(bess_msg_pb2.CreatePortRequest(
                name=nameVNFPMDPort1,driver="PMDPort",num_inc_q=1,
                num_out_q=1, size_inc_q=0, size_out_q=0, arg=argument))
            self._checkResponse(response)

            # QueueInc()
            nameQueueInc = "vhostpmd_in_" + str(vnfi.VNFIID)
            argument = Any()
            argument.Pack( module_msg_pb2.QueueIncArg(port=nameVNFPMDPort0,
                qid=0))
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name=nameQueueInc,mclass="QueueInc",arg=argument))
            self._checkResponse(response)
            # QueueOut()
            nameQueueOut = "vhostpmd_out_" + str(vnfi.VNFIID)
            argument = Any()
            argument.Pack( module_msg_pb2.QueueOutArg(port=nameVNFPMDPort1,
                qid=0))
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name=nameQueueOut,mclass="QueueOut",arg=argument))
            self._checkResponse(response)

            if nextVNFID != -1:
                # Update
                nameUpdate = "update_" + str(vnfi.VNFIID)
                offset = 31
                size = 2
                value = self._getUpdateValue(SFCID,nextVNFID)
                argument = Any()
                argument.Pack( module_msg_pb2.UpdateArg( fields=[
                    {"offset":offset, "size":size, "value": value }] ))
                response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                    name=nameUpdate,mclass="Update",arg=argument))
                self._checkResponse(response)
            else:
                # GenericDecap
                nameGenericDecap = "genericDecap_" + str(vnfi.VNFIID)
                argument = Any()
                argument.Pack( module_msg_pb2.GenericDecapArg( bytes=20 ))
                response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                    name=nameGenericDecap,mclass="GenericDecap",arg=argument))
                self._checkResponse(response)

            # connection
            # em -> nameQueueOut
            bessServerIP = bessServerUrl.split(":")[0]
            emPort = self._serverSet[bessServerIP]["BessState"].exactMatchState[vnfi.serverDatapathNICIP[0]]
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1="em",m2=nameQueueOut,ogate=emPort,igate=0))
            self._checkResponse(response)

            if nextVNFID != -1:
                # nameQueueInc -> nameUpdate
                response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                    m1=nameQueueInc,m2=nameUpdate,ogate=0,igate=0))
                self._checkResponse(response)

                # nameUpdate -> em
                response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                    m1=nameUpdate,m2="em",ogate=0,igate=0))
                self._checkResponse(response)
            else:
                # nameQueueInc -> nameGenericDecap
                response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                    m1=nameQueueInc,m2=nameGenericDecap,ogate=0,igate=0))
                self._checkResponse(response)
                #  nameGenericDecap -> outputmerge
                response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                    m1=nameGenericDecap,m2="outmerge",ogate=0,igate=0))
                self._checkResponse(response)

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

    def _getUpdateValue(self,SFCID,nextVNFID):
        return ((SFCID & 0xFFF) << 4) + (nextVNFID & 0XF)

    def _delSFCinBESS(self,cmd):
        sfc = cmd.attributes['sfc']
        for vnfiList in sfc.VNFISeq:
            for vnfi in vnfiList:
                # init new server
                if not vnfi.serverControlNICIP in self._serverSet:
                    continue
                # del VNF PMDPort
                index = sfc.VNFISeq.index(vnfiList)
                nextVNFID = -1
                if index < len(sfc.VNFISeq)-1:
                    nextVNFID = sfc.VNFISeq[index+1][0].VNFID
                self._delVNFDataPath(vnfi.serverControlNICIP + ":10514",vnfi,sfc.SFCID,nextVNFID)
                # del rules in exactmatch
                self._delDataPathRule(vnfi.serverControlNICIP + ":10514",vnfi)

    def _delVNFDataPath(self,bessServerUrl,vnfi,SFCID,nextVNFID):
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            nameQueueOut = "vhostpmd_out_" + str(vnfi.VNFIID)
            nameQueueInc = "vhostpmd_in_" + str(vnfi.VNFIID)
            nameUpdate = "update_" + str(vnfi.VNFIID)
            nameGenericDecap = "genericDecap_" + str(vnfi.VNFIID)

            # disconnection
            # em -> nameQueueOut
            bessServerIP = bessServerUrl.split(":")[0]
            emPort = self._serverSet[bessServerIP]["BessState"].exactMatchState[vnfi.serverDatapathNICIP[0]]
            response = stub.DisconnectModules(bess_msg_pb2.DisconnectModulesRequest(
                name="em",ogate=emPort))
            self._checkResponse(response)

            if nextVNFID != -1:
                # nameQueueInc -> nameUpdate
                response = stub.DisconnectModules(bess_msg_pb2.DisconnectModulesRequest(
                    name=nameQueueInc,ogate=0))
                self._checkResponse(response)

                # nameUpdate -> em
                response = stub.DisconnectModules(bess_msg_pb2.DisconnectModulesRequest(
                    name=nameUpdate,ogate=0))
                self._checkResponse(response)
            else:
                # ameQueueInc -> nameGenericDecap
                response = stub.DisconnectModules(bess_msg_pb2.DisconnectModulesRequest(
                    name=nameQueueInc,ogate=0))
                self._checkResponse(response)
                #  nameGenericDecap -> outputmerge
                response = stub.DisconnectModules(bess_msg_pb2.DisconnectModulesRequest(
                    name=nameGenericDecap,ogate=0))
                self._checkResponse(response)

            # destory module
            if nextVNFID != -1:
                # Update
                response = stub.DestroyModule(bess_msg_pb2.DestroyModuleRequest(
                    name=nameUpdate))
                self._checkResponse(response)
            else:
                # GenericDecap
                response = stub.DestroyModule(bess_msg_pb2.DestroyModuleRequest(
                    name=nameGenericDecap))
                self._checkResponse(response)

            # QueueInc()
            response = stub.DestroyModule(bess_msg_pb2.DestroyModuleRequest(
                name=nameQueueInc))
            self._checkResponse(response)
            # QueueOut()
            response = stub.DestroyModule(bess_msg_pb2.DestroyModuleRequest(
                name=nameQueueOut))
            self._checkResponse(response)

            # PMDPort
            # PMDPort()
            vdevVNFPMDPORT0 = self.getVdevOfVNFOutputPMDPort(vnfi.VNFIID)
            nameVNFPMDPort0 = self._getNameOfVNFOutputPMDPort(vnfi.VNFIID)
            response = stub.DestroyPort(bess_msg_pb2.DestroyPortRequest(
                name=nameVNFPMDPort0))
            self._checkResponse(response)
            # PMDPort()
            vdevVNFPMDPORT1 = self._getVdevOfVNFInputPMDPort(vnfi.VNFIID)
            nameVNFPMDPort1 = self._getNameOfVNFInputPMDPort(vnfi.VNFIID)
            response = stub.DestroyPort(bess_msg_pb2.DestroyPortRequest(
                name=nameVNFPMDPort1))
            self._checkResponse(response)

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

    def _delDataPathRule(self,bessServerUrl,vnfi):
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            # add rule to em
            argument = Any()
            bessServerIP = bessServerUrl.split(":")[0]
            gatePort = self._getAvailableEmPort( self._serverSet[bessServerIP]["BessState"] )
            for ip in vnfi.serverDatapathNICIP:
                logging.debug("sffController.serverSet.bessState.ExactMatch.matchfield = ip:%s, gatePort:%d." %(ip, gatePort) )
                argument.Pack(module_msg_pb2.ExactMatchCommandDeleteArg(
                    fields=[{"value_bin":self._sc.aton(ip)}]
                    ))
                response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(
                    name="em",cmd="delete",arg=argument))
                self._checkResponse(response)
                del self._serverSet[bessServerIP]["BessState"].exactMatchState[ip]

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

    def _getVNFIStatus(self,cmd):
        pass

if __name__=="__main__":
    logging.basicConfig(level=logging.INFO)
    sffController = BESSController()
    sffController.startBESSController()