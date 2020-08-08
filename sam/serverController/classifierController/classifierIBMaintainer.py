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
import Queue
import struct

import sam.serverController.builtin_pb.service_pb2 as service_pb2
import sam.serverController.builtin_pb.service_pb2_grpc as service_pb2_grpc
import sam.serverController.builtin_pb.bess_msg_pb2 as bess_msg_pb2
import sam.serverController.builtin_pb.module_msg_pb2 as module_msg_pb2
import sam.serverController.builtin_pb.ports.port_msg_pb2 as port_msg_pb2

from sam.base.server import Server
from sam.base.messageAgent import *
from sam.base.sfc import *
from sam.base.socketConverter import SocketConverter as SC
from sam.base.command import *
from sam.base.path import *

# Classifier set maintainer's responsibilities
# 1: active classifier
# 2: classifier - sfc mapping
# 3: sfc - sfci mapping
# 4: active sfc sets

class Classifier(object):
    def __init__(self,host):
        self.host = host    # The server hosting this classifier
        self.wm2Gate = {}   # {HashLBName: gateNum}
        self.hlbGate = {}   # {HashLBName: {GenricDecapNAME: gateNum}}

class ClassifierIBMaintainer(object):
    def __init__(self):
        self.classifiers = {} # {serverID: {"classifier":classifier,"state":True} }

    def initClassifier(self,ingress):
        serverID = ingress.getServerID()
        classifier = Classifier(ingress)
        self.classifiers[serverID] = classifier

    def isClassifierInit(self,ingress):
        serverID = ingress.getServerID()
        return serverID in self.classifiers.iterkeys()

    def addSFC2Classifier(self,sfc,wm2GateNum,hlbName):
        for direction in sfc.directions:
            ingress = direction['ingress']
            serverID = ingress.getServerID()
            classifier = self.classifiers[serverID]
            directionID = direction['ID']
            self.classifiers[serverID].wm2Gate[hlbName] = wm2GateNum
            self.classifiers[serverID].hlbGate[hlbName] = {}

    def delSFC2Classifier(self,ingress,sfc):
        pass

    def addSFCI2Classifier(self,ingress,sfc,sfci):
        pass

    def delSFCI2Classifier(self,ingress,sfc,sfci):
        pass

    def genHashLBName(self,sfcUUID,directionID):
        pass

    def genGenericDecapName(self,sfciid,directionID):
        pass

    def genSetMetaDataName(self,sfciid,directionID):
        pass

    def genIPEncapName(self,sfciid,directionID):
        pass

    def getWM2GateNum(self,ingress,hashLBName):
        pass

    def getHashLBGateNum(self,ingress,genericDecapName):
        pass

    def genWM2GateNum(self,ingress):
        pass

    def genHashLBGateNum(self,ingress,hashLBName):
        pass

    def delWM2GateNum(self,hashLBName):
        pass

    def delHashLBGateNum(self,genericDecapName):
        pass

