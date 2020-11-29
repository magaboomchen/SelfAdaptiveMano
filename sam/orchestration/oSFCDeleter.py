#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid

import networkx

from sam.base.sfc import *
from sam.base.vnf import *
from sam.base.switch import *
from sam.base.link import *
from sam.base.server import *
from sam.base.path import *
from sam.base.command import *
from sam.base.socketConverter import SocketConverter
from sam.orchestration.pathComputer import *
from sam.orchestration.orchestrator import *
from sam.orchestration.oConfig import *


class OSFCDeleter(object):
    def __init__(self, dib, logger):
        self._dib = dib
        self.logger = logger

    def genDelSFCCmd(self, request):
        self.request = request
        self._checkRequest()

        self.sfc = self.request.attributes['sfc']
        self.zoneName = self.sfc.attributes["zone"]

        cmd = Command(CMD_TYPE_DEL_SFC, uuid.uuid1(), attributes={
            'sfc':self.sfc, 'zone':self.zoneName
        })

        return cmd

    def genDelSFCICmd(self, request):
        self.request = request
        self._checkRequest()

        self.sfc = self.request.attributes['sfc']
        self.zoneName = self.sfc.attributes["zone"]
        self.sfci = self.request.attributes['sfci']

        cmd = Command(CMD_TYPE_DEL_SFCI, uuid.uuid1(), attributes={
            'sfc':self.sfc, 'sfci':self.sfci, 'zone':self.zoneName
        })

        return cmd

    def _checkRequest(self):
        if 'sfc' not in self.request.attributes:
            raise ValueError("Request missing sfc")
