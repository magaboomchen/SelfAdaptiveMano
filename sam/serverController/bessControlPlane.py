#!/usr/bin/python
# -*- coding: UTF-8 -*-

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
import struct

import sam.serverController.builtin_pb.service_pb2 as service_pb2
import sam.serverController.builtin_pb.service_pb2_grpc as service_pb2_grpc
import sam.serverController.builtin_pb.bess_msg_pb2 as bess_msg_pb2
import sam.serverController.builtin_pb.module_msg_pb2 as module_msg_pb2
import sam.serverController.builtin_pb.ports.port_msg_pb2 as port_msg_pb2

from sam.base.socketConverter import SocketConverter
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.server import *
from sam.base.exceptionProcessor import ExceptionProcessor


class BessControlPlane(object):
    def __init__(self):
        self._sc = SocketConverter()
        logConfigur = LoggerConfigurator(__name__, './log',
            'bessControlPlane.log', level='info')
        self.logger = logConfigur.getLogger()

    def isBESSAlive(self,bessServerUrl):
        count = 3
        while count > 0:
            try:
                with grpc.insecure_channel(bessServerUrl) as channel:
                    stub = service_pb2_grpc.BESSControlStub(channel)
                    response = stub.GetVersion(bess_msg_pb2.EmptyRequest())
                return True
            except Exception as ex:
                ExceptionProcessor(self.logger).logException(ex,
                    " isBESSAlive ")
                count = count - 1
        return False

    def _checkResponse(self,response):
        if response.error.code != 0:
            self.logger.error( str(response.error) )
            raise ValueError('bess cmd failed.')

    def _getWM2Rule(self, match):
        values=[
            {"value_bin":b'\x00'},
            {"value_bin":b'\x00\x00\x00\x00'},
            {"value_bin":b'\x00\x00\x00\x00'},
            {"value_bin":b'\x00\x00'},
            {"value_bin":b'\x00\x00'}
        ]
        masks=[
            {'value_bin':b'\x00'},
            {'value_bin':b'\x00\x00\x00\x00'},
            {'value_bin':b'\x00\x00\x00\x00'},
            {'value_bin':b'\x00\x00'},
            {'value_bin':b'\x00\x00'}
        ]
        if match['proto'] != "*":
            values[0]["value_bin"] = match['proto']
            masks[0]["value_bin"] = b'\xFF'
        if match['srcIP'] != "*":
            values[1]["value_bin"] = self._sc.aton(match['srcIP'])
            masks[1]["value_bin"] = b'\xFF\xFF\xFF\xFF'
        if match['dstIP'] != "*":
            values[2]["value_bin"] = self._sc.aton(match['dstIP'])
            masks[2]["value_bin"] = b'\xFF\xFF\xFF\xFF'
        if match['srcPort'] != "*":
            values[3]["value_bin"] = self._sc.aton(match['srcPort'])
            masks[3]["value_bin"] = b'\xFF\xFF'
        if match['dstPort'] != "*":
            values[4]["value_bin"] = self._sc.aton(match['dstPort'])
            masks[4]["value_bin"] = b'\xFF\xFF'
        return [values,masks]

    def _genIP4SVPIDs(self,sfcID,vnfID,pathID):
        ipNum = (10<<24) + ((vnfID & 0xF) << 20) + ((sfcID & 0xFFF) << 8) \
            + (pathID & 0xFF)
        return self._sc.int2ip(ipNum)

    def getSFCIModuleSuffix(self,sfciID,direction):
        return '_' + str(sfciID) + '_' + str(direction['ID'])

    def getSFCModuleSuffix(self,sfcUUID,direction):
        return '_' + str(sfcUUID) + '_' + str(direction['ID'])

    def _checkVNFISequence(self, vnfiSequence):
        for vnf in vnfiSequence:
            for i in range(len(vnf)-1):
                for j in range(i+1,len(vnf)-1):
                    vnfi1 = vnf[i]
                    vnfi2 = vnf[j]
                    if isinstance(vnfi1.node, Server) and\
                        vnfi1.node.getServerID() == vnfi2.node.getServerID():
                        raise ValueError(
                            'Backup VNFI can\'t be placed in the same server.')