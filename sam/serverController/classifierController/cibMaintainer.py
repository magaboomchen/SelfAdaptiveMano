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

from sam.base.server import Server
from sam.base.messageAgent import *
from sam.base.sfc import *
from sam.base.command import *
from sam.base.path import *
from sam.serverController.bessInfoBaseMaintainer import *

# TODO: need test

class CIBMS(object):
    def __init__(self):
        self._cibms = {} # {serverID:CIBMaintainer}

    def hasCibm(self, serverID):
        return self._cibms.has_key(serverID)

    def addCibm(self,serverID):
        self._cibms[serverID] = CIBMaintainer()

    def getCibm(self, serverID):
        return self._cibms[serverID]

class CIBMaintainer(BessInfoBaseMaintainer):
    '''Classifiers Information Base Maintainer'''
    def __init__(self, *args, **kwargs):
        super(CIBMaintainer, self).__init__(*args, **kwargs)
        self._sfcSet = {}   # {sfcUUID:[sfciid]}

    def addSFCDirection(self,sfcUUID,directionID):
        self._sfcSet[(sfcUUID,directionID)] = []

    def delSFCDirection(self,sfcUUID,directionID):
        del self._sfcSet[(sfcUUID,directionID)]

    def addSFCIDirection(self,sfcUUID,directionID,SFCIID):
        self._sfcSet[(sfcUUID,directionID)].append(SFCIID)

    def delSFCIDirection(self,sfcUUID,directionID,SFCIID):
        self._sfcSet[(sfcUUID,directionID)].remove(SFCIID)

    def canDeleteSFCDirection(self,sfcUUID,directionID):
        return self._sfcSet[(sfcUUID,directionID)] == []

    def hasSFCDirection(self,sfcUUID,direction):
        return self._sfcSet.has_key((sfcUUID,direction))

    def getHashLBName(self,sfcUUID,directionID):
        mclass = "HashLB"
        moduleNameSuffix = '_' + str(sfcUUID) + '_' + str(directionID['ID'])
        return mclass + moduleNameSuffix