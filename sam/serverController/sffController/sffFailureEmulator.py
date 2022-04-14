#!/usr/bin/python
# -*- coding: UTF-8 -*-

import grpc

import sam.serverController.builtin_pb.service_pb2_grpc as service_pb2_grpc
import sam.serverController.builtin_pb.bess_msg_pb2 as bess_msg_pb2
from sam.serverController.bessControlPlane import BessControlPlane


class SFFFailureEmulator(BessControlPlane):
    def __init__(self, sibms, logger):
        self.sibms = sibms
        self.logger = logger

    def emulateSoftwareFailure(self, cmd):
        serverList = cmd.attributes["serverDown"]
        for server in serverList:
            self.logger.info("Pausing server: {0}".format(server))
            serverControlIP = server.getControlNICIP()
            serverID = server.getServerID()
            bessServerUrl = serverControlIP + ":10514"
            if self.isBESSAlive(bessServerUrl):
                self._pauseBESS(bessServerUrl)
            else:
                raise ValueError("BESS is not alive!")

    def _pauseBESS(self, bessServerUrl):
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.PauseAll(bess_msg_pb2.EmptyRequest())

    def emulateSoftwareFailureRecovery(self, cmd):
        serverList = cmd.attributes["serverUp"]
        for server in serverList:
            self.logger.info("Resuming server: {0}".format(server))
            serverControlIP = server.getControlNICIP()
            serverID = server.getServerID()
            bessServerUrl = serverControlIP + ":10514"
            if self.isBESSAlive(bessServerUrl):
                self._resumeBESS(bessServerUrl)
            else:
                raise ValueError("BESS is not alive!")

    def _resumeBESS(self, bessServerUrl):
        with grpc.insecure_channel(bessServerUrl) as channel:
            stub = service_pb2_grpc.BESSControlStub(channel)
            stub.ResumeAll(bess_msg_pb2.EmptyRequest())
