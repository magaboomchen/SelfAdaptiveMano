#!/usr/bin/python
# -*- coding: UTF-8 -*-

from __future__ import print_function
import grpc
from google.protobuf.any_pb2 import Any

import sam.serverController.builtin_pb.service_pb2_grpc as service_pb2_grpc
import sam.serverController.builtin_pb.bess_msg_pb2 as bess_msg_pb2
import sam.serverController.builtin_pb.module_msg_pb2 as module_msg_pb2
from sam.serverController.bessControlPlane import BessControlPlane
from sam.serverController.classifierController.classifierInitializer import ClassifierInitializer


class ClassifierSFCAdder(BessControlPlane):
    def __init__(self,cibms,logger):
        super(ClassifierSFCAdder,self).__init__()
        self.cibms = cibms
        self.logger = logger
        self.clsfSFCInitializer = ClassifierInitializer(self.cibms, logger)

    def addSFCHandler(self,cmd):
        sfc = cmd.attributes['sfc']
        sfcUUID = sfc.sfcUUID
        for direction in sfc.directions:
            classifier = direction['ingress']
            serverID = classifier.getServerID()
            if not self.cibms.hasCibm(serverID):
                self.clsfSFCInitializer.initClassifier(direction)
            cibm = self.cibms.getCibm(serverID)
            if not cibm.hasSFCDirection(sfcUUID,direction["ID"]):
                self.addSFC(sfcUUID,direction)
            cibm.addSFCDirection(sfcUUID,direction['ID'])

    def addSFC(self,sfcUUID,direction):
        classifier = direction['ingress']
        serverID = classifier.getServerID()
        cibm = self.cibms.getCibm(serverID)
        self._addModules(classifier,sfcUUID,direction)
        self._addRules(classifier,sfcUUID,direction)
        self._addLinks(classifier,sfcUUID,direction)
        cibm.addSFCDirection(sfcUUID,direction['ID'])

    def _addModules(self,classifier,sfcUUID,direction):
        serverID = classifier.getServerID()
        cibm = self.cibms.getCibm(serverID)

        bessServerUrl = classifier.getControlNICIP() + ":10514"
        self.logger.info(bessServerUrl)
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            mclass = "HashLB"
            moduleName = cibm.getHashLBName(sfcUUID,direction)

            # HashLB()
            argument = Any()
            arg = module_msg_pb2.HashLBArg(mode="l3")
            argument.Pack(arg)
            response = stub.CreateModule(bess_msg_pb2.CreateModuleRequest(
                name=moduleName,mclass=mclass,arg=argument))
            self._checkResponse(response)

            cibm.addModule(moduleName,mclass)

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

    def _addRules(self,classifier,sfcUUID,direction):
        bessServerUrl = classifier.getControlNICIP() + ":10514"
        self.logger.info(bessServerUrl)
        match = direction['match']
        serverID = classifier.getServerID()
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            # Rule
            # Add match
            argument = Any()
            gateNum = self._assignWM2OGate(serverID,sfcUUID)
            [values,masks] = self._getWM2Rule(match)
            arg = module_msg_pb2.WildcardMatchCommandAddArg(gate=gateNum,
                values=values, masks=masks)
            argument.Pack(arg)
            response = stub.ModuleCommand(bess_msg_pb2.CommandRequest(
                name="wm2",cmd="add",arg=argument))

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())

    def _assignWM2OGate(self,serverID,sfcUUID):
        cibm = self.cibms.getCibm(serverID)
        OGateList = cibm.getModuleOGateNumList('wm2')
        oGateNum = cibm.genAvailableMiniNum4List(OGateList)
        cibm.addOGate2Module('wm2',sfcUUID,oGateNum)
        return oGateNum

    def _addLinks(self,classifier,sfcUUID,direction):
        serverID = classifier.getServerID()
        cibm = self.cibms.getCibm(serverID)

        bessServerUrl = classifier.getControlNICIP() + ":10514"
        self.logger.info(bessServerUrl)
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

            moduleName = cibm.getHashLBName(sfcUUID,direction)

            # Connection
            # wm2 -> HashLB()'s name
            ogate = cibm.getModuleOGate('wm2',sfcUUID)
            response = stub.ConnectModules(bess_msg_pb2.ConnectModulesRequest(
                m1="wm2",m2=moduleName,ogate=ogate,igate=0))
            self._checkResponse(response)

            stub.ResumeAll(bess_msg_pb2.EmptyRequest())