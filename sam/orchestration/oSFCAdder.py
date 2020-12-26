#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid
import copy

import networkx

from sam.base.sfc import *
from sam.base.vnf import *
from sam.base.switch import *
from sam.base.link import *
from sam.base.server import *
from sam.base.path import *
from sam.base.command import *
from sam.base.socketConverter import SocketConverter
from sam.orchestration.oConfig import *
from sam.orchestration.pathComputer import *
from sam.orchestration.orchestrator import *
from sam.orchestration.algorithms.pSFC import *
from sam.orchestration.algorithms.opSFC import *
from sam.orchestration.algorithms.notVia import *


class OSFCAdder(object):
    def __init__(self, dib, logger):
        self._dib = dib
        self.logger = logger
        self._sc = SocketConverter()

    def genAddSFCCmd(self, request):
        self.request = request
        self._checkRequest()

        self.sfc = self.request.attributes['sfc']
        self.zoneName = self.sfc.attributes["zone"]

        self._mapIngressEgress()
        self.logger.debug("sfc:{0}".format(self.sfc))

        cmd = Command(CMD_TYPE_ADD_SFC, uuid.uuid1(), attributes={
            'sfc':self.sfc, 'zone':self.zoneName
        })

        return cmd

    def genAddSFCICmd(self, request):
        self.request = request
        self._checkRequest()

        self.sfc = self.request.attributes['sfc']
        self.zoneName = self.sfc.attributes["zone"]
        self.sfci = self.request.attributes['sfci']

        self._mapIngressEgress()    # TODO: get sfc from database
        self.logger.debug("sfc:{0}".format(self.sfc))

        self._mapVNFI()
        self.logger.debug("sfci:{0}".format(self.sfci))

        self._mapForwardingPath()
        self.logger.debug("ForwardingPath:{0}".format(
            self.sfci.forwardingPathSet))

        cmd = Command(CMD_TYPE_ADD_SFCI, uuid.uuid1(), attributes={
            'sfc':self.sfc, 'sfci':self.sfci, 'zone':self.zoneName
        })

        return cmd

    def _checkRequest(self):
        if self.request.requestType  == REQUEST_TYPE_ADD_SFCI or\
            self.request.requestType  == REQUEST_TYPE_DEL_SFCI:
            if 'sfc' not in self.request.attributes:
                raise ValueError("Request missing sfc")
            if 'sfci' not in self.request.attributes:
                raise ValueError("Request missing sfci")
        elif self.request.requestType  == REQUEST_TYPE_ADD_SFC or\
            self.request.requestType  == REQUEST_TYPE_DEL_SFC:
            if 'sfc' not in self.request.attributes:
                raise ValueError("Request missing sfc")
        else:
            raise ValueError("Unknown request type.")

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

            for serverInfo in self._dib.getServersByZone(self.zoneName).values():
                server = serverInfo['server']
                ip = server.getDatapathNICIP()
                serverType = server.getServerType()
                if self._sc.isInSameLAN(nodeIP, ip, LANIPPrefix) and\
                    serverType == SERVER_TYPE_CLASSIFIER:
                    return server
            else:
                raise ValueError("Find ingress/egress failed")

    def _getDCNGateway(self):
        dcnGateway = None
        switchDict = self._dib.getSwitchesByZone(self.zoneName)
        for switch in switchDict.itervalues():
            # self.logger.debug(switch)
            if switch.switchType == SWITCH_TYPE_DCNGATEWAY:
                # self.logger.debug(
                #     "switch.switchType:{0}".format(switch.switchType)
                #     )
                dcnGateway = switch
                break
        else:
            raise ValueError("Find DCN Gateway failed")
        return dcnGateway

    def _getClassifierBySwitch(self, switch):
        self.logger.debug(self._dib.getServersByZone(self.zoneName))
        for serverInfo in self._dib.getServersByZone(self.zoneName).values():
            server = serverInfo['server']
            self.logger.debug(server)
            ip = server.getDatapathNICIP()
            self.logger.debug(ip)
            serverType = server.getServerType()
            if serverType == SERVER_TYPE_CLASSIFIER:
                self.logger.debug(
                    "server type is classifier " \
                    "ip:{0}, switch.lanNet:{1}".format(ip, switch.lanNet))
            if self._sc.isLANIP(ip, switch.lanNet) and \
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
        self.sfci.vnfiSequence = vSeq

    def _roundRobinSelectServers(self, vnfType, iNum):
        vnfiList = []
        for serverInfo in self._dib.getServersByZone(self.zoneName).values():
            server = serverInfo['server']
            if server.getServerType() == 'nfvi':
                vnfi = VNFI(vnfType, vnfType, uuid.uuid1(), None, server)
                vnfiList.append(vnfi)
        return vnfiList

    def _mapForwardingPath(self):
        self._pC = PathComputer(self._dib, self.request, self.sfci,
            self.logger)
        self._pC.mapPrimaryFP()
        if self.sfci.forwardingPathSet.frrType != None:
            self._pC.mapBackupFP()

    def genABatchOfRequestAndAddSFCICmds(self, requestBatchQueue):
        # while not requestBatchQueue.empty():
        #     request = requestBatchQueue.get()
        #     self.logger.info("request:{0}".format(request))
        #     self.logger.info("sfci:{0}".format(request.attributes["sfci"]))

        # self.logger.debug(requestBatchQueue)
        # raw_input()

        requestDict = self._divRequest(requestBatchQueue)
        for frrType in requestDict.keys():
            if frrType == 'FRR_TYPE_UFRR':
                self.logger.info("ufrr")
            elif frrType == 'FRR_TYPE_E2EP':
                self.logger.info("e2ep")
            elif frrType == 'FRR_TYPE_NOTVIA_PSFC':
                self.logger.info("PSFC NotVia")

                # self.logger.debug(requestDict['FRR_TYPE_NOTVIA_PSFC'])
                # raw_input()

                opSFC = OPSFC(self._dib, requestDict['FRR_TYPE_NOTVIA_PSFC'])
                mapResults = opSFC.mapSFCI()

                pSFC = PSFC(self._dib, requestDict['FRR_TYPE_NOTVIA_PSFC'],
                    mapResults)
                mapResults = pSFC.mapSFCI()

                notVia = NotVia(self._dib, 
                    requestDict['FRR_TYPE_NOTVIA_PSFC'], mapResults)
                mapResults = notVia.mapSFCI()
            else:
                self.logger.error("Unknown frrType.")
                raise ValueError("Unknown frrType.")

        return mapResults

    def _divRequest(self, requestBatchQueue):
        requestDict = {}
        while not requestBatchQueue.empty():
            request = copy.deepcopy(requestBatchQueue.get())
            # self.logger.debug(request)
            # self.logger.debug("*****************")
            # raw_input()
            frrType = request.attributes['frrType']
            if frrType not in requestDict.keys():
                requestDict[frrType] = []
            requestDict[frrType].append(request)
            # self.logger.debug(requestDict[frrType])
            # raw_input()
        return requestDict
