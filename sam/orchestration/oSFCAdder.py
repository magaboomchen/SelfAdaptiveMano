#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid
import logging

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
from sam.orchestration.orchestrator import LANIPPrefix



class OSFCAdder(object):
    def __init__(self, dib):
        self._dib = dib
        self._sc = SocketConverter()

    def genAddSFCICmd(self, request):
        self.request = request
        self._checkRequest()

        self.sfc = self.request.attributes['sfc']
        self.zoneName = self.sfc.attributes["zone"]
        self.sfci = SFCI(uuid.uuid1(), [],
            ForwardingPathSet=ForwardingPathSet({},"UFRR",{}))

        self._mapIngressEgress()
        # logging.info("sfc:{0}".format(self.sfc))

        self._mapVNFI()
        # logging.info("sfci:{0}".format(self.sfci))

        self._mapForwardingPath()
        # logging.info("ForwardingPath:{0}".format(self.sfci.ForwardingPathSet))
        
        cmd =Command(CMD_TYPE_ADD_SFCI, uuid.uuid1(), attributes={
            'sfc':self.sfc, 'sfci':self.sfci, 'zone':self.zoneName
        })
        return cmd

    def _checkRequest(self):
        if 'sfc' not in self.request.attributes:
            raise ValueError("Request missing sfc")

    def _mapIngressEgress(self):
        for direction in self.sfc.directions:
            source = direction['source']
            direction['ingress'] = self._selectClassifier(source)

            destination = direction['destination']
            direction['egress'] = self._selectClassifier(destination)

    def _selectClassifier(self, node):
        if node == None:
            dcnGateway = self._getDCNGateway()
            return self._getClassifierBySwitch(dcnGateway)
        else:
            if "IPv4" in node:
                nodeIP = node["IPv4"]
            else:
                raise ValueError("Unsupport source/destination type")

            for server in self._dib.getServersByZone(self.zoneName):
                ip = server.getControlNICIP()
                serverType = server.getServerType()
                if self._sc.isInSameLAN(nodeIP, ip, LANIPPrefix) and\
                    serverType == SERVER_TYPE_CLASSIFIER:
                    return server
            else:
                raise ValueError("Find ingress/egress failed")

    def _getDCNGateway(self):
        dcnGateway = None
        for switch in self._dib.getSwitchesByZone(self.zoneName):
            if switch.switchType == SWITCH_TYPE_DCNGATEWAY:
                logging.debug(
                    "switch.switchType:{0}".format(switch.switchType)
                    )
                dcnGateway = switch
                break
        else:
            raise ValueError("Find DCN Gateway failed")
        return dcnGateway

    def _getClassifierBySwitch(self, switch):
        for server in self._dib.getServersByZone(self.zoneName):
            ip = server.getControlNICIP()
            serverType = server.getServerType()
            if self._sc.isLANIP(ip, switch.LanNet) and\
                serverType == SERVER_TYPE_CLASSIFIER:
                return server
        else:
            raise ValueError("Find ingress/egress failed")

    def _mapVNFI(self):
        iNum = self.sfc.backupInstanceNumber
        length = len(self.sfc.vNFTypeSequence)
        vSeq = []
        for stage in range(length):
            vnfType = self.sfc.vNFTypeSequence[stage]
            vnfiList = self._roundRobinSelectServers(vnfType, iNum)
            vSeq.append(vnfiList)
        self.sfci.VNFISequence = vSeq

    def _roundRobinSelectServers(self, vnfType, iNum):
        vnfiList = []
        servers = self._dib.getServersByZone(self.zoneName)
        for server in servers:
            if server.getServerType() == 'nfvi':
                vnfi = VNFI(vnfType, vnfType, uuid.uuid1(), None, server)
                vnfiList.append(vnfi)
        return vnfiList

    def _mapForwardingPath(self):
        self._pC = PathComputer(self._dib, self.request, self.sfci)
        self._pC.mapPrimaryFP()
        self._pC.mapBackupFP()

