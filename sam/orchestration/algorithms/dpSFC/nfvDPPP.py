#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
 dedicated protection sfc mapping
[2018][icc]Resource Requirements for
Reliable Service Function Chaining
'''

import copy

import numpy as np
import gurobipy as gp
from gurobipy import GRB
from gurobipy import *

from sam.base.path import *
from sam.base.server import *
from sam.base.messageAgent import *
from sam.base.socketConverter import *
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.orchestration.algorithms.base.mappingAlgorithmBase import *


class NFVDPPricingProblem(MappingAlgorithmBase):
    def __init__(self, dib, requestList):
        self._dib = dib
        self.requestList = requestList

        logConfigur = LoggerConfigurator(__name__,
            './log', 'NFVDPPricingProblem.log', level='warning')
        self.logger = logConfigur.getLogger()

        self._init()

    def _init(self):
        request = self.requestList[0]
        self.zoneName = request.attributes['zone']
        self._pathLinkVar = {}
        self._vnfDeployVar = {}
        self._genPhysicalLink()
        self._genSwitch()
        self._genRequestIngAndEg()
        self.ppModel = {}
        self.ppModelObj = {}

    def _genPhysicalLink(self):
        # cap: link
        self.links = {}
        for key, link in self._dib.getLinksByZone(self.zoneName).items():
            (srcNodeID, dstNodeID) = key
            self.links[(srcNodeID, dstNodeID)] \
                = self._dib.getLinkResidualResource(
                    srcNodeID, dstNodeID, self.zoneName)

        self.physicalLink , self.linkCapacity = gp.multidict(self.links)

        # self.logger.debug("phsicalLink:{0}, self.linkCapacity:{1}".format(
        #     self.physicalLink, self.linkCapacity))

    def _genSwitch(self):
        # cap: vNode
        self.switches = {}
        for switchID, switch in self._dib.getSwitchesByZone(self.zoneName).items():
            self.switches[switchID] = [self._dib.getNPoPServersCapacity(switchID,
                self.zoneName)]
        self.switches, self.switchCapacity = gp.multidict(self.switches)
        # self.logger.debug("switches:{0}".format(self.switches))

    def _genRequestIngAndEg(self):
        self.requestIngSwitchID = {}
        self.requestEgSwitchID = {}
        for rIndex in range(len(self.requestList)):
            request = self.requestList[rIndex]
            sfc = request.attributes['sfc']
            ingress = sfc.directions[0]['ingress']
            egress = sfc.directions[0]['egress']
            ingSwitch = self._dib.getConnectedSwitch(ingress.getServerID(),
                self.zoneName)
            ingSwitchID = ingSwitch.switchID
            egSwitch = self._dib.getConnectedSwitch(egress.getServerID(),
                self.zoneName)
            egSwitchID = egSwitch.switchID
            self.logger.debug("ingSwitchID:{0}, egSwitchID:{1}".format(
                ingSwitchID,egSwitchID))
            self.requestIngSwitchID[rIndex] = ingSwitchID
            self.requestEgSwitchID[rIndex] = egSwitchID
        self.logger.debug("self.requestIngSwitchID:{0}".format(self.requestIngSwitchID))

    def initPPs(self, dualVars):
        self.dualVars = dualVars
        for rIndex in range(len(self.requestList)):
            self._initPP(rIndex, 'p')
            self._initPP(rIndex, 'b')

    def _initPP(self, rIndex, pb):
        if not self._hasPP(rIndex, pb):
            self._genPP(rIndex, pb)
        else:
            self._updateMIPObj(rIndex, pb)

    def _hasPP(self, rIndex, pb):
        if (rIndex, pb) in self.ppModel.keys():
            return True
        else:
            return False

    def _genPP(self, rIndex, pb):
        self._genVariablesAndConsts(rIndex, pb)
        self._trans2MIP(rIndex, pb)

    def _genVariablesAndConsts(self, rIndex, pb):
        self._genPathLinkVar(rIndex, pb) # [rIndex, pb][i, srcID, dstID]: 1
        self._genVNFNodeVar(rIndex, pb)  # [rIndex, pb][i, switchID]: 0

    def _genPathLinkVar(self, rIndex, pb):
        if (rIndex,pb) not in self._pathLinkVar.keys():
            self._pathLinkVar[rIndex, pb] = {}
        request = self.requestList[rIndex]
        sfc = self.getSFC4Request(request)
        vnfSeq = sfc.vNFTypeSequence
        for vnfIndex in range(len(vnfSeq)+1):
            for srcID, dstID in self.physicalLink:
                self._pathLinkVar[rIndex, pb][vnfIndex, srcID, dstID] = 1

    def _genVNFNodeVar(self, rIndex, pb):
        if (rIndex,pb) not in self._vnfDeployVar.keys():
            self._vnfDeployVar[rIndex, pb] = {}
        request = self.requestList[rIndex]
        sfc = self.getSFC4Request(request)
        vnfSeq = sfc.vNFTypeSequence
        for vnfIndex in range(len(vnfSeq)+1):
            for switchID in self.switches:
                self._vnfDeployVar[rIndex, pb][vnfIndex, switchID] = 1

    def _trans2MIP(self, rIndex, pb):
        try:
            if (rIndex, pb) not in self.ppModel.keys():
                self.ppModel[rIndex, pb] = {}

            request = self.requestList[rIndex]
            sfc = self.getSFC4Request(request)
            vnfSeq = sfc.vNFTypeSequence

            # Create optimization model
            self.ppModel[rIndex, pb] = gp.Model(
                'nfvDPPP[{0},{1}]'.format(rIndex, pb))

            # timeout setting
            self.ppModel[rIndex, pb].setParam('TimeLimit', 1000)

            # Create continuous variables
            phi = self.ppModel[rIndex, pb].addVars(
                    self._pathLinkVar[rIndex, pb],
                    vtype=GRB.BINARY, name="flow", lb=0.0, ub=1.0)

            a = self.ppModel[rIndex, pb].addVars(
                    self._vnfDeployVar[rIndex, pb],
                    vtype=GRB.BINARY, name="deploy", lb=0.0, ub=1.0)

            # Flow-conservation constraints
            self.ppModel[rIndex, pb].addConstrs(
                (   phi.sum(0, switchID, '*') - phi.sum(0, '*', switchID) \
                    + a.sum(0, switchID) == 1
                    for switchID in self.switches if switchID == self.requestIngSwitchID[rIndex]
                    ), "srcNode")

            self.ppModel[rIndex, pb].addConstrs(
                (   phi.sum(0, switchID, '*') - phi.sum(0, '*', switchID) \
                    + a.sum(0, switchID) == 0
                    for switchID in self.switches if switchID != self.requestIngSwitchID[rIndex]
                    ), "srcNode")

            self.ppModel[rIndex, pb].addConstrs(
                (   phi.sum(vnfIndex, switchID, '*') - phi.sum(vnfIndex, '*', switchID) \
                    + a.sum(vnfIndex, switchID) - a.sum(vnfIndex-1, switchID) == 0
                    for switchID in self.switches
                    for vnfIndex in range(1, len(vnfSeq)+1)
                ), "middleNode")

            # link capacity constraints


            # node capacity constraints


            # latency capacity constraints


            # Add model obj
            # TODO
            # self._updateMIPObj(rIndex, pb)
            # self.ppModel[rIndex, pb].setObjective(self.modelObj, GRB.MINIMIZE)
            self.ppModel[rIndex, pb].update()
            self.ppModel[rIndex, pb].write("./nfvDPPP.lp")

        except GurobiError:
            self.logger.error('Error reported')

        finally:
            pass

    def _updateMIPObj(self, rIndex, pb):
        self.ppModelObj[rIndex, pb] = None
        # TODO
        return self.ppModelObj[rIndex, pb]

    def solveAllPPs(self):
        pass

    def hasBetterConfigurations(self):
        pass

    def getConfigurations(self):
        pass
