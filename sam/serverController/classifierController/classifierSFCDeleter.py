#!/usr/bin/python
# -*- coding: UTF-8 -*-

from __future__ import print_function
import grpc
from google.protobuf.any_pb2 import Any
import logging

import sam.serverController.builtin_pb.service_pb2 as service_pb2
import sam.serverController.builtin_pb.service_pb2_grpc as service_pb2_grpc
import sam.serverController.builtin_pb.bess_msg_pb2 as bess_msg_pb2
import sam.serverController.builtin_pb.module_msg_pb2 as module_msg_pb2
import sam.serverController.builtin_pb.ports.port_msg_pb2 as port_msg_pb2

from sam.serverController.bessControlPlane import *

class ClassifierSFCDeleter(BessControlPlane):
    def __init__(self,cibms):
        super(ClassifierSFCDeleter,self).__init__()
        self.cibms = cibms

    def delSFC(self,sfc,direction):
        sfcUUID = sfc.sfcUUID
        classifier = direction['ingress']
        serverID = classifier.getServerID()
        cibm = self.cibms.getCibm(serverID)
        self._delLinks(classifier,sfcUUID,direction)
        self._delRules(classifier,sfcUUID,direction)
        self._delModules(classifier,sfcUUID,direction)
        cibm.delSFCDirection(sfcUUID,direction["ID"])
        # update wm2 ogate
    
    def _delLinks(self,classifier,sfcUUID,direction):
        serverID = classifier.getServerID()
        cibm = self.cibms.getCibm(serverID)

        bessServerUrl = classifier.getControlNICIP() + ":10514"
        logging.info(bessServerUrl)
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            moduleName = cibm.getHashLBName(sfcUUID,direction)

            # Connection
            # wm2 -> HashLB()'s name
            ogate = cibm.getModuleOGate('wm2',sfcUUID)
            response = stub.DisconnectModules(bess_msg_pb2.DisconnectModulesRequest(
                name="wm2",ogate=ogate))
            self._checkResponse(response)

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

    def _delRules(self,classifier,sfcUUID,direction):
        bessServerUrl = classifier.getControlNICIP() + ":10514"
        logging.info(bessServerUrl)
        match = direction['match']
        serverID = classifier.getServerID()
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            # Rule
            # Del match
            argument = Any()
            [values,masks] = self._getWM2Rule(match)
            arg = module_msg_pb2.WildcardMatchCommandDeleteArg(
                values=values, masks=masks)
            argument.Pack(arg)
            response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(
                name="wm2",cmd="delete",arg=argument))
            self._checkResponse(response)

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

    def _delModules(self,classifier,sfcUUID,direction):
        serverID = classifier.getServerID()
        cibm = self.cibms.getCibm(serverID)

        bessServerUrl = classifier.getControlNICIP() + ":10514"
        logging.info(bessServerUrl)
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            mclass = "HashLB"
            moduleName = cibm.getHashLBName(sfcUUID,direction)

            # HashLB()
            response = stub.DestroyModule(bess_msg_pb2.DestroyModuleRequest(
                name=moduleName))
            self._checkResponse(response)

            cibm.delModule(moduleName)

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())