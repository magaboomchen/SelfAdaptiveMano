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
from sam.base.mkdirs import *
from sam.base.messageAgent import *
from sam.base.socketConverter import *
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.orchestration.algorithms.base.mappingAlgorithmBase import *


class NFVDPPricingProblem(MappingAlgorithmBase):
    def __init__(self, dib, requestList):
        self._dib = dib
        self.requestList = requestList

        logConfigur = LoggerConfigurator(__name__,
            './log', 'NFVDPPricingProblem.log', level='info')
        self.logger = logConfigur.getLogger()

        self._init()

    def _init(self):
        request = self.requestList[0]
        self.zoneName = request.attributes['zone']
        self._pathLinkVar = {}
        self._vnfDeployVar = {}
        self._resConsumeCoeff = {}
        self._linkLatency = {}
        self._vnfLatency = {}
        self._genPhysicalLink()
        self._genSwitch()
        self._genRequestIngAndEg()
        self.ppModel = {}
        self.ppModelObj = {}
        self.phi = {}
        self.a = {}

    def _genPhysicalLink(self):
        # cap: link
        self.links = {}
        for key in self._dib.getLinksByZone(self.zoneName).keys():
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
        for switchID, switchInfoDict in self._dib.getSwitchesByZone(self.zoneName).items():
            switch = switchInfoDict['switch']
            self.switches[switchID] = [self._dib.getNPoPServersCapacity(switchID,
                self.zoneName)]
        self.switches, self.switchCapacity = gp.multidict(self.switches)
        # self.logger.debug("switches:{0}".format(self.switches))

    # implemented in MappingAlgorithmBase
    # def _genRequestIngAndEg(self):
    #     self.requestIngSwitchID = {}
    #     self.requestEgSwitchID = {}
    #     for rIndex in range(len(self.requestList)):
    #         request = self.requestList[rIndex]
    #         sfc = request.attributes['sfc']
    #         ingress = sfc.directions[0]['ingress']
    #         egress = sfc.directions[0]['egress']
    #         ingSwitch = self._dib.getConnectedSwitch(ingress.getServerID(),
    #             self.zoneName)
    #         ingSwitchID = ingSwitch.switchID
    #         egSwitch = self._dib.getConnectedSwitch(egress.getServerID(),
    #             self.zoneName)
    #         egSwitchID = egSwitch.switchID
    #         self.logger.debug("ingSwitchID:{0}, egSwitchID:{1}".format(
    #             ingSwitchID,egSwitchID))
    #         self.requestIngSwitchID[rIndex] = ingSwitchID
    #         self.requestEgSwitchID[rIndex] = egSwitchID
    #     self.logger.debug("self.requestIngSwitchID:{0}".format(self.requestIngSwitchID))

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
        self._genVNFResConsume(rIndex, pb)  # [rIndex, pb][i, switchID]: resConsu
        self._genLinkLatency(rIndex, pb)
        self._genVNFLatency(rIndex, pb)

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

    def _genVNFResConsume(self, rIndex, pb):
        if (rIndex, pb) not in self._resConsumeCoeff.keys():
            self._resConsumeCoeff[rIndex, pb] = {}
        request = self.requestList[rIndex]
        sfc = self.getSFC4Request(request)
        trafficDemand = sfc.getSFCTrafficDemand()
        vnfSeq = sfc.vNFTypeSequence
        pM = PerformanceModel()
        for vnfIndex in range(len(vnfSeq)+1):
            for switchID in self.switches:
                if vnfIndex == len(vnfSeq):
                    self._resConsumeCoeff[rIndex, pb][vnfIndex, switchID] = 0
                else:
                    vnfType = vnfSeq[vnfIndex]
                    coreConsume = pM.getExpectedServerResource(vnfType, 
                        trafficDemand)[0]
                    self._resConsumeCoeff[rIndex, pb][vnfIndex,
                        switchID] = coreConsume

    def _genLinkLatency(self, rIndex, pb):
        if (rIndex, pb) not in self._linkLatency.keys():
            self._linkLatency[rIndex, pb] = {}
        request = self.requestList[rIndex]
        sfc = self.getSFC4Request(request)
        vnfSeq = sfc.vNFTypeSequence
        pM = PerformanceModel()
        for vnfIndex in range(len(vnfSeq)+1):
            for srcID, dstID in self.physicalLink:
                link = self._dib.getLink(srcID, dstID, self.zoneName)
                pLatency = pM.getPropogationLatency(link.linkLength)
                self._linkLatency[rIndex, pb][vnfIndex, srcID, dstID] = pLatency

    def _genVNFLatency(self, rIndex, pb):
        if (rIndex, pb) not in self._vnfLatency.keys():
            self._vnfLatency[rIndex, pb] = {}
        request = self.requestList[rIndex]
        sfc = self.getSFC4Request(request)
        trafficDemand = sfc.getSFCTrafficDemand()
        vnfSeq = sfc.vNFTypeSequence
        pM = PerformanceModel()
        for vnfIndex in range(len(vnfSeq)+1):
            for switchID in self.switches:
                if vnfIndex == len(vnfSeq):
                    self._vnfLatency[rIndex, pb][vnfIndex, switchID] = 0
                else:
                    vnfType = vnfSeq[vnfIndex]
                    vnfLatency = pM.getLatencyOfVNF(vnfType, trafficDemand)
                    self._vnfLatency[rIndex, pb][vnfIndex, switchID] = vnfLatency

    def _trans2MIP(self, rIndex, pb):
        try:
            if (rIndex, pb) not in self.ppModel.keys():
                self.ppModel[rIndex, pb] = {}

            request = self.requestList[rIndex]
            egSwitchID = self.getEgSwitchID4Request(request)
            sfc = self.getSFC4Request(request)
            vnfSeq = sfc.vNFTypeSequence
            trafficDemand = sfc.getSFCTrafficDemand()
            latencyBound = sfc.getSFCLatencyBound()

            # Create optimization model
            self.ppModel[rIndex, pb] = gp.Model(
                'nfvDPPP[{0},{1}]'.format(rIndex, pb))

            # timeout setting
            self.ppModel[rIndex, pb].setParam('TimeLimit', 1000)

            # Create continuous variables
            self.phi[rIndex, pb] = self.ppModel[rIndex, pb].addVars(
                    self._pathLinkVar[rIndex, pb],
                    vtype=GRB.BINARY, name="flow", lb=0.0, ub=1.0)

            self.a[rIndex, pb] = self.ppModel[rIndex, pb].addVars(
                    self._vnfDeployVar[rIndex, pb],
                    vtype=GRB.BINARY, name="deploy", lb=0.0, ub=1.0)

            # Flow-conservation constraints
            self.ppModel[rIndex, pb].addConstrs(
                (   self.phi[rIndex, pb].sum(0, switchID, '*') - self.phi[rIndex, pb].sum(0, '*', switchID) \
                    + self.a[rIndex, pb].sum(0, switchID) == 1
                    for switchID in self.switches if switchID == self.requestIngSwitchID[rIndex]
                    ), "srcNode")

            self.ppModel[rIndex, pb].addConstrs(
                (   self.phi[rIndex, pb].sum(0, switchID, '*') - self.phi[rIndex, pb].sum(0, '*', switchID) \
                    + self.a[rIndex, pb].sum(0, switchID) == 0
                    for switchID in self.switches if switchID != self.requestIngSwitchID[rIndex]
                    ), "srcNode")

            self.ppModel[rIndex, pb].addConstrs(
                (   self.phi[rIndex, pb].sum(vnfIndex, switchID, '*') - self.phi[rIndex, pb].sum(vnfIndex, '*', switchID) \
                    + self.a[rIndex, pb].sum(vnfIndex, switchID) - self.a[rIndex, pb].sum(vnfIndex-1, switchID) == 0
                    for switchID in self.switches
                    for vnfIndex in range(1, len(vnfSeq)+1)
                ), "middleNode")

            # fixed dst node
            self.ppModel[rIndex, pb].addConstrs(
                (   
                    self.a[rIndex, pb].sum(len(vnfSeq), switchID) == 1
                    for switchID in self.switches if switchID == egSwitchID
                ), "dstNode")

            # exactly one node to deploy an vnf
            self.ppModel[rIndex, pb].addConstrs(
                (   
                    self.a[rIndex, pb].sum(vnfIndex, '*') == 1
                    for vnfIndex in range(len(vnfSeq))
                ), "vnfUnSplittable")

            # NPoP provide correspoing vnf
            self.ppModel[rIndex, pb].addConstrs(
                (   
                    self.a[rIndex, pb].sum(vnfIndex, [switchID for switchID in self.switches
                        if (vnfSeq[vnfIndex] in self._dib.getSwitch(switchID, self.zoneName).supportVNF) ]
                        ) == 1
                    for vnfIndex in range(len(vnfSeq))
                ), "vnfDeployable")

            # link capacity constraints
            self.ppModel[rIndex, pb].addConstrs(
                (   self.phi[rIndex, pb].sum('*', srcID, dstID) <= self.linkCapacity[srcID, dstID] / trafficDemand
                    for srcID, dstID in self.physicalLink
                ), "linkCapacity")

            # node capacity constraints
            self.ppModel[rIndex, pb].addConstrs(
                (   self.a[rIndex, pb].prod(self._resConsumeCoeff[rIndex, pb], '*', switchID) <= self.switchCapacity[switchID]
                    for switchID in self.switches
                ), "nodeCapacity")

            # latency capacity constraints
            self.ppModel[rIndex, pb].addConstr(
                (   self.phi[rIndex, pb].prod(self._linkLatency[rIndex, pb], '*', '*', '*') \
                    + self.a[rIndex, pb].prod(self._vnfLatency[rIndex, pb], '*', '*') <= latencyBound
                ), "e2eLatency")

            # Add model obj
            self._updateMIPObj(rIndex, pb)
            self.ppModel[rIndex, pb].setObjective(self.ppModelObj[rIndex, pb], GRB.MINIMIZE)
            self.ppModel[rIndex, pb].update()
            mkdirs("./LP/")
            self.ppModel[rIndex, pb].write("./LP/nfvDPPP_{0}_{1}.lp".format(rIndex, pb))

        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex)
            raise ValueError("gurobipy error")

        finally:
            pass

    def _updateMIPObj(self, rIndex, pb):
        request = self.requestList[rIndex]
        sfc = self.getSFC4Request(request)
        vnfSeq = sfc.vNFTypeSequence
        trafficDemand = sfc.getSFCTrafficDemand()
        pM = PerformanceModel()

        self.ppModelObj[rIndex, pb] = LinExpr()

        # first polynomial
        for vnfIndex in range(len(vnfSeq)+1):
            for srcID, dstID in self.physicalLink:
                self.ppModelObj[rIndex, pb] \
                    += self.phi[rIndex, pb].sum(vnfIndex, srcID, dstID) \
                        * trafficDemand

        # second polynomial
        if pb == 'p':
            self.ppModelObj[rIndex, pb] += -1 * self.dualVars['constr10a'][rIndex, pb]
        elif pb == 'b':
            self.ppModelObj[rIndex, pb] += -1 * self.dualVars['constr10b'][rIndex, pb]
        else:
            raise ValueError("Unknown pb:{0}".format(pb))

        # third polynomial
        for vnfIndex in range(len(vnfSeq)+1):
            for srcID, dstID in self.physicalLink:
                self.ppModelObj[rIndex, pb] \
                    += -1 * self.phi[rIndex, pb].sum(vnfIndex, srcID, dstID) \
                        * self.dualVars['constr11'][rIndex, srcID, dstID]

        # 4-th polynomial
        for vnfIndex in range(len(vnfSeq)+1):
            for srcID, dstID in self.physicalLink:
                self.ppModelObj[rIndex, pb] \
                    += self.phi[rIndex, pb].sum(vnfIndex, srcID, dstID) \
                        * self.dualVars['constr12'][srcID, dstID] \
                        * trafficDemand

        # 5-th polynomial
        for vnfIndex in range(len(vnfSeq)+1):
            for switchID in self.switches:
                self.ppModelObj[rIndex, pb] \
                    += self.dualVars['constr13'][switchID] \
                        * trafficDemand \
                        * self._resConsumeCoeff[rIndex, pb][vnfIndex, switchID]

    def solveAllPPs(self):
        for rIndex in range(len(self.requestList)):
            for pb in ['p', 'b']:

                self.ppModel[rIndex, pb].optimize()

                if self.ppModel[rIndex, pb].status == GRB.OPTIMAL:
                    self.logger.info("model status: optimal")
                    self.logSolution(rIndex, pb)
                elif self.ppModel[rIndex, pb].status == GRB.SUBOPTIMAL:
                    self.logger.warning("model status: suboptimal")
                elif self.ppModel[rIndex, pb].status == GRB.INFEASIBLE:
                    self.logger.warning("infeasible model")
                    raise ValueError("infeasible model")
                else:
                    self.logger.warning("unknown model status:{0}".format(m.status))

    def logSolution(self, rIndex, pb):
        request = self.requestList[rIndex]
        sfc = self.getSFC4Request(request)
        vnfSeq = sfc.vNFTypeSequence

        # phi
        self.phiSolution = self.ppModel[rIndex, pb].getAttr('x',
            self.phi[rIndex, pb])
        for vnfIndex in range(len(vnfSeq)+1):
            for srcID, dstID in self.physicalLink:
                if self.phiSolution[vnfIndex, srcID, dstID] > 0:
                    self.logger.info(
                        "phiSolution[{0},{1},{2}]:{3}".format(
                            vnfIndex, srcID, dstID,
                            self.phiSolution[vnfIndex, srcID, dstID]))

        # a
        self.aSolution = self.ppModel[rIndex, pb].getAttr('x',
            self.a[rIndex, pb])
        for vnfIndex in range(len(vnfSeq)+1):
            for switchID in self.switches:
                if self.aSolution[vnfIndex, switchID] > 0:
                    self.logger.info(
                        "aSolution[{0},{1}]:{2}".format(
                            vnfIndex, switchID,
                            self.aSolution[vnfIndex, switchID]))

    def hasBetterConfigurations(self):
        for rIndex in range(len(self.requestList)):
            for pb in ['p', 'b']:
                obj = self.ppModel[rIndex, pb].getObjective()
                if obj.getValue() < 0:
                    self.logger.warning("obj.getValue:{0}".format(
                        obj.getValue() ))
                    return True
        return False

    def getConfigurations(self):
        self.newConfigurations = {}
        for rIndex in range(len(self.requestList)):
            request = self.requestList[rIndex]
            for pb in ['p', 'b']:
                obj = self.ppModel[rIndex, pb].getObjective()
                if obj.getValue() < 0:
                    path = self._getPaths(rIndex, pb)
                    self._addPath2NewConfigurations(request, path)
        return self.newConfigurations

    def _getPaths(self, rIndex, pb):
        request = self.requestList[rIndex]
        sfc = self.getSFC4Request(request)
        vnfSeq = sfc.vNFTypeSequence

        self.logger.info("rIndex:{0}, pb:{1}".format(rIndex, pb))

        # generate raw path
        self.phiSolution = self.ppModel[rIndex, pb].getAttr('x',
            self.phi[rIndex, pb])
        linkDict = {}
        for vnfIndex in range(len(vnfSeq)+1):
            for srcID, dstID in self.physicalLink:
                if self.phiSolution[vnfIndex, srcID, dstID] > 0:
                    self.logger.info(
                        "phiSolution[{0},{1},{2}]:{3}".format(
                            vnfIndex, srcID, dstID,
                            self.phiSolution[vnfIndex, srcID, dstID]))
                    if vnfIndex not in linkDict.keys():
                        linkDict[vnfIndex] = []
                    linkDict[vnfIndex].append((srcID, dstID))
        path = self._genPath4LinkDict(linkDict)
        self.logger.info("path:{0}".format(path))

        # insert missing layer if multiple vnfs deployed in same NPoP
        self.aSolution = self.ppModel[rIndex, pb].getAttr('x',
            self.a[rIndex, pb])
        nPopDict = {}
        for vnfIndex in range(len(vnfSeq)+1):
            for switchID in self.switches:
                if self.aSolution[vnfIndex, switchID] > 0:
                    self.logger.info(
                        "aSolution[{0},{1}]:{2}".format(
                            vnfIndex, switchID,
                            self.aSolution[vnfIndex, switchID]))
                    nPopDict[vnfIndex] = switchID
        path = self._insertMissingLayer(path, nPopDict)
        self.logger.info("rIndex:{0}, pb:{1}, path:{2}".format(
            rIndex, pb, path))
        return path

    def _addPath2NewConfigurations(self, request, path):
        sdc = self._getSDC(request)
        if sdc not in self.newConfigurations.keys():
            self.newConfigurations[sdc] = []
        self.newConfigurations[sdc].append(path)
