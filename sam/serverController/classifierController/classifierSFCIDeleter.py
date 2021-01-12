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
from sam.serverController.bessInfoBaseMaintainer import *
from sam.serverController.classifierController.classifierSFCDeleter import *


class ClassifierSFCIDeleter(BessControlPlane):
    def __init__(self, cibms, logger):
        super(ClassifierSFCIDeleter,self).__init__()
        self.cibms = cibms
        self.logger = logger

    def delSFCIHandler(self,cmd):
        sfc = cmd.attributes['sfc']
        sfci = cmd.attributes['sfci']
        sfcUUID = sfc.sfcUUID
        sfciID = sfci.sfciID
        self.logger.debug("delSFCI sfcUUID:{0}, sfciID:{1}".format(
            sfcUUID, sfciID
        ))
        for direction in sfc.directions:
            classifier = direction['ingress']
            serverID = classifier.getServerID()
            self.logger.debug("delSFCIHandler serverID:{0}".format(serverID))
            if not self.cibms.hasCibm(serverID):
                self.logger.warning("not self.cibms.hasCibm(serverID)")
                continue
            cibm = self.cibms.getCibm(serverID)
            if not cibm.hasSFCDirection(sfcUUID,direction['ID']):
                self.logger.warning("not cibm.hasSFCDirection(sfcUUID,direction['ID'])")
                continue
            self._delLinks(sfcUUID,sfci,direction)
            self._delRules(sfcUUID,sfci,direction)
            self._delModules(sfcUUID,sfci,direction)
            cibm.delSFCIDirection(sfcUUID,direction['ID'],sfciID)

            sfcSet = cibm.getSFCSet()
            self.logger.debug("After delete SFCI, cibm:{0}".format(sfcSet))

    def _delLinks(self,sfcUUID,sfci,direction):
        classifier = direction['ingress']
        serverID = classifier.getServerID()
        cibm = self.cibms.getCibm(serverID)
        sfciID = sfci.sfciID

        bessServerUrl = classifier.getControlNICIP() + ":10514"
        self.logger.info(bessServerUrl)
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            hashLBName = cibm.getHashLBName(sfcUUID,direction)

            moduleNameSuffix = self.getSFCIModuleSuffix(sfciID,direction)
            mclass = "GenericDecap"
            genericDecapName = mclass + moduleNameSuffix

            mclass = "SetMetadata"
            SetMetaDataName = mclass + moduleNameSuffix

            mclass = "IPEncap"
            IPEncapName = mclass + moduleNameSuffix

            # Connection
            # hlb: gate -> gd
            ogate = cibm.getModuleOGate(hashLBName,sfciID)
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
        sfciID = sfci.sfciID

        bessServerUrl = classifier.getControlNICIP() + ":10514"
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            hashLBName = cibm.getHashLBName(sfcUUID,direction)

            # add hash LB gate
            argument = Any()
            gateNumList = self._deleteHashLBOGateofSFCI(serverID,sfcUUID,
                direction, sfciID)
            arg = module_msg_pb2.HashLBCommandSetGatesArg(gates=gateNumList)
            argument.Pack(arg)
            response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(
                name=hashLBName,cmd="add",arg=argument))

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

    def _deleteHashLBOGateofSFCI(self,serverID,sfcUUID,direction, sfciID):
        cibm = self.cibms.getCibm(serverID)
        hashLBName = cibm.getHashLBName(sfcUUID,direction)
        oGate = cibm.getModuleOGate(hashLBName,sfciID)
        OGateList = cibm.getModuleOGateNumList(hashLBName)
        OGateList.remove(oGate)
        cibm.delModuleOGate(hashLBName,sfciID)
        return OGateList

    def _delModules(self,sfcUUID,sfci,direction):
        classifier = direction['ingress']
        serverID = classifier.getServerID()
        cibm = self.cibms.getCibm(serverID)
        sfciID = sfci.sfciID

        bessServerUrl = classifier.getControlNICIP() + ":10514"
        self.logger.info(bessServerUrl)
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            moduleNameSuffix = self.getSFCIModuleSuffix(sfciID,direction)

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