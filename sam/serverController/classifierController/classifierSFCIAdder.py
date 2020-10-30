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
from sam.serverController.classifierController.classifierInitializer import *
from sam.serverController.classifierController.classifierSFCAdder import *

class ClassifierSFCIAdder(BessControlPlane):
    def __init__(self,cibms,logger):
        super(ClassifierSFCIAdder,self).__init__()
        self.cibms = cibms
        self.logger = logger
        self.clsfSFCInitializer = ClassifierInitializer(self.cibms, logger)
        self.clsfSFCAdder = ClassifierSFCAdder(self.cibms, logger)

    def addSFCIHandler(self,cmd):
        sfc = cmd.attributes['sfc']
        sfci = cmd.attributes['sfci']
        sfcUUID = sfc.sfcUUID
        SFCIID = sfci.SFCIID
        for direction in sfc.directions:
            classifier = direction['ingress']
            serverID = classifier.getServerID()
            if not self.cibms.hasCibm(serverID):
                self.clsfSFCInitializer.initClassifier(direction)
            cibm = self.cibms.getCibm(serverID)
            if not cibm.hasSFCDirection(sfcUUID,direction["ID"]):
                self.clsfSFCAdder.addSFC(sfcUUID,direction)
            self._addModules(sfc,sfcUUID,sfci,direction)
            self._addRules(sfcUUID,sfci,direction)
            self._addLinks(sfcUUID,sfci,direction)
            cibm.addSFCIDirection(sfcUUID,direction['ID'],SFCIID)

    def _addModules(self,sfc,sfcUUID,sfci,direction):
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
            argument = Any()
            arg = module_msg_pb2.GenericDecapArg(bytes=14)
            argument.Pack(arg)
            mclass = "GenericDecap"
            moduleName = mclass + moduleNameSuffix
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name=moduleName, mclass=mclass, arg=argument))
            self._checkResponse(response)

            # SetMetaData()
            argument = Any()
            tunnelSrcIP = self._sc.aton(classifier.getDatapathNICIP())
            if direction['ID'] == 0:
                VNFID = sfc.vNFTypeSequence[0]
                PathID = DIRECTION1_PATHID_OFFSET
            else:
                VNFID = sfc.vNFTypeSequence[0]
                PathID = DIRECTION2_PATHID_OFFSET
            tunnelDstIP = self._sc.aton(self._genIP4SVPIDs(SFCIID,VNFID,PathID))
            arg = module_msg_pb2.SetMetadataArg(attrs=[
                {'name':"ip_src", 'size':4, 'value_bin':tunnelSrcIP},
                {'name':"ip_dst", 'size':4, 'value_bin':tunnelDstIP},
                {'name':"ip_proto", 'size':1, 'value_bin':b'\x04'},
                {'name':"ether_type", 'size':2, 'value_bin': b'\x08\x00'}
            ])
            argument.Pack(arg)
            mclass = "SetMetadata"
            moduleName = mclass + moduleNameSuffix
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name=moduleName,mclass=mclass,arg=argument))
            self._checkResponse(response)

            # IPEncap()
            argument = Any()
            arg = module_msg_pb2.IPEncapArg()
            argument.Pack(arg)
            mclass = "IPEncap"
            moduleName = mclass + moduleNameSuffix
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name=moduleName,mclass=mclass,arg=argument))
            self._checkResponse(response)

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

    def _addRules(self,sfcUUID,sfci,direction):
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
            gateNumList = cibm.assignHashLBOGatesList(serverID,sfcUUID,
                direction, SFCIID)
            arg = module_msg_pb2.HashLBCommandSetGatesArg(gates=gateNumList)
            argument.Pack(arg)
            response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(
                name=hashLBName,cmd="add",arg=argument))

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

    def _addLinks(self,sfcUUID,sfci,direction):
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
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1=hashLBName,m2=genericDecapName,ogate=ogate,igate=0))
            self._checkResponse(response)

            # gd -> sma
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1=genericDecapName,m2=SetMetaDataName,ogate=0,igate=0))
            self._checkResponse(response)

            # sma -> ipe
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1=SetMetaDataName,m2=IPEncapName,ogate=0,igate=0))
            self._checkResponse(response)

            # ipe -> etherEncapMerge
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1=IPEncapName,m2='etherEncapMerge',ogate=0,igate=0))
            self._checkResponse(response)

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())