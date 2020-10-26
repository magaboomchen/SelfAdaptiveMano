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
from sam.serverController.bessInfoBaseMaintainer import *
from sam.serverController.classifierController.classifierSFCDeleter import *

class ClassifierSFCIDeleter(BessControlPlane):
    def __init__(self, cibms, logger):
        super(ClassifierSFCIDeleter,self).__init__()
        self.cibms = cibms
        self.logger = logger
        self.clsfSFCDeleter = ClassifierSFCDeleter(self.cibms, logger)

    def delSFCIHandler(self,cmd):
        sfc = cmd.attributes['sfc']
        sfci = cmd.attributes['sfci']
        sfcUUID = sfc.sfcUUID
        SFCIID = sfci.SFCIID
        for direction in sfc.directions:
            classifier = direction['ingress']
            serverID = classifier.getServerID()
            if not self.cibms.hasCibm(serverID):
                return
            cibm = self.cibms.getCibm(serverID)
            if not cibm.hasSFCDirection(sfcUUID,direction['ID']):
                return
            self._delLinks(sfcUUID,sfci,direction)
            self._delRules(sfcUUID,sfci,direction)
            self._delModules(sfcUUID,sfci,direction)
            cibm.delSFCIDirection(sfcUUID,direction['ID'],SFCIID)
            
            if cibm.canDeleteSFCDirection(sfcUUID,direction["ID"]) == True:
                self.clsfSFCDeleter.delSFC(sfc,direction)

    def _delLinks(self,sfcUUID,sfci,direction):
        classifier = direction['ingress']
        serverID = classifier.getServerID()
        cibm = self.cibms.getCibm(serverID)
        SFCIID = sfci.SFCIID

        bessServerUrl = classifier.getControlNICIP() + ":10514"
        self.logger.info(bessServerUrl)
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            hashLBName = cibm.getHashLBName(sfcUUID,direction)

            moduleNameSuffix = self.getSFCIModuleSuffix(SFCIID,direction)
            mclass = "GenericDecap"
            genericDecapName = mclass + moduleNameSuffix

            mclass = "SetMetadata"
            SetMetaDataName = mclass + moduleNameSuffix

            mclass = "IPEncap"
            IPEncapName = mclass + moduleNameSuffix

            # Connection
            # hlb: gate -> gd
            ogate = cibm.getModuleOGate(hashLBName,SFCIID)
            response = stub.DisconnectModules(bess_msg_pb2.DisconnectModulesRequest(
                name=hashLBName,ogate=ogate))
            self._checkResponse(response)

            # gd -> sma
            response = stub.DisconnectModules(bess_msg_pb2.DisconnectModulesRequest(
                name=genericDecapName,ogate=0))
            self._checkResponse(response)

            # sma -> ipe
            response = stub.DisconnectModules(bess_msg_pb2.DisconnectModulesRequest(
                name=SetMetaDataName,ogate=0))
            self._checkResponse(response)

            # ipe -> etherEncapMerge
            response = stub.DisconnectModules(bess_msg_pb2.DisconnectModulesRequest(
                name=IPEncapName,ogate=0))
            self._checkResponse(response)

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

    def _delRules(self,sfcUUID,sfci,direction):
        classifier = direction['ingress']
        serverID = classifier.getServerID()
        cibm = self.cibms.getCibm(serverID)
        SFCIID = sfci.SFCIID

        bessServerUrl = classifier.getControlNICIP() + ":10514"
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            hashLBName = cibm.getHashLBName(sfcUUID,direction)

            # add hash LB gate
            argument = Any()
            gateNumList = self._deleteHashLBOGateofSFCI(serverID,sfcUUID,
                direction, SFCIID)
            arg = module_msg_pb2.HashLBCommandSetGatesArg(gates=gateNumList)
            argument.Pack(arg)
            response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(
                name=hashLBName,cmd="add",arg=argument))

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

    def _deleteHashLBOGateofSFCI(self,serverID,sfcUUID,direction, SFCIID):
        cibm = self.cibms.getCibm(serverID)
        hashLBName = cibm.getHashLBName(sfcUUID,direction)
        oGate = cibm.getModuleOGate(hashLBName,SFCIID)
        OGateList = cibm.getModuleOGateNumList(hashLBName)
        OGateList.remove(oGate)
        cibm.delModuleOGate(hashLBName,SFCIID)
        return OGateList

    def _delModules(self,sfcUUID,sfci,direction):
        classifier = direction['ingress']
        serverID = classifier.getServerID()
        cibm = self.cibms.getCibm(serverID)
        SFCIID = sfci.SFCIID

        bessServerUrl = classifier.getControlNICIP() + ":10514"
        self.logger.info(bessServerUrl)
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            moduleNameSuffix = self.getSFCIModuleSuffix(SFCIID,direction)

            # GenericDecap()
            mclass = "GenericDecap"
            moduleName = mclass + moduleNameSuffix
            response = stub.DestroyModule(bess_msg_pb2.DestroyModuleRequest(
                name=moduleName))
            self._checkResponse(response)

            # SetMetaData()
            mclass = "SetMetadata"
            moduleName = mclass + moduleNameSuffix
            response = stub.DestroyModule(bess_msg_pb2.DestroyModuleRequest(
                name=moduleName))
            self._checkResponse(response)

            # IPEncap()
            mclass = "IPEncap"
            moduleName = mclass + moduleNameSuffix
            response = stub.DestroyModule(bess_msg_pb2.DestroyModuleRequest(
                name=moduleName))
            self._checkResponse(response)

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())