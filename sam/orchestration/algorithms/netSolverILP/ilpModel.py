#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
[2020][AI]Scalable constraint-based virtual data center allocation
'''

import copy
from random import randrange

import numpy as np
import gurobipy as gp
from gurobipy import GRB
from gurobipy import *

from sam.base.vnf import *
from sam.base.path import *
from sam.base.server import *
from sam.base.mkdirs import *
from sam.base.messageAgent import *
from sam.base.socketConverter import *
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.orchestration.algorithms.base.multiLayerGraph import *
from sam.orchestration.algorithms.base.mappingAlgorithmBase import *
from sam.orchestration.algorithms.oPSFC.opRandomizedRoundingAlgorithm import *

INITIAL_PATH_PER_REQUEST_NUM = 2


class ILPModel(OPRandomizedRoundingAlgorithm):
    def __init__(self, dib, requestList):
        self._dib = dib
        self.requestList = requestList

        logConfigur = LoggerConfigurator(__name__,
            './log', 'ILPModel.log', level='debug')
        self.logger = logConfigur.getLogger()

        self.zoneName = self.requestList[0].attributes['zone']

    def loadFatTreeArg(self, podNum, minPodIdx, maxPodIdx):
        self.logger.info(
            "loadArg podNum:{0} minPodIdx:{1} maxPodIdx:{2}".format(
                                podNum, minPodIdx, maxPodIdx))
        self.podNum = podNum
        self.minPodIdx = minPodIdx
        self.maxPodIdx = maxPodIdx

    def initModel(self):
        self._initEnvModel()

    def updateModel(self):
        self._genVariablesAndConsts()
        self._trans2ILP()

    def _initEnvModel(self):
        self.env = gp.Env()
        self.model = gp.Model('netSolverILP', self.env)

    def _genVariablesAndConsts(self):
        self._genPhysicalLink()
        self._genSwitch()
        self._genRequestIngAndEg()
        self._pathLinkVar = {}
        self._vnfDeployVar = {}
        self._resConsumeCoeff = {}
        for rIndex in range(len(self.requestList)):
            # self.logger.info("rIndex: {0}".format(rIndex))
            self._genPathLinkVar(rIndex) # [rIndex][i, srcID, dstID]: 1
            self._genVNFNodeVar(rIndex)  # [rIndex][i, switchID]: 0
            self._genVNFResConsume(rIndex)  # [rIndex][i, switchID]: resConsu
        # self.logger.info("pathlinkvar rindxs: {0}".format(self._pathLinkVar.keys()))

    def _genPhysicalLink(self):
        # cap: link
        self.links = {}
        for key in self._dib.getLinksByZone(self.zoneName).keys():
            (srcNodeID, dstNodeID) = key
            # self.logger.info("key: {0}".format(key))
            if (self._dib.isServerID(srcNodeID) 
                    or self._dib.isServerID(dstNodeID)):
                continue
            self.links[(srcNodeID, dstNodeID)] \
                = self._dib.getLinkResidualResource(
                    srcNodeID, dstNodeID, self.zoneName)

        self.physicalLink, self.linkCapacity = gp.multidict(self.links)

        # self.logger.info("self.physicalLink: {0}".format(self.physicalLink))

        # for link,capacity in self.linkCapacity.items():
        #     if capacity < 1:
        #         self.logger.debug("nfvDPPP, link:{0}, capacity:{1}".format(
        #             link, capacity))
        #         raw_input()

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

    def _genRequestIngAndEg(self):
        self.requestIngSwitchID = {}
        self.requestEgSwitchID = {}
        for rIndex in range(len(self.requestList)):
            request = self.requestList[rIndex]
            sfc = request.attributes['sfc']
            vnfSeqList = sfc.vNFTypeSequence
            try:
                ingSwitchID = self.getIngSwitchID4Request(request)
                egSwitchID = self.getEgSwitchID4Request(request)
            except:
                ingSwitchID = self._randomSelectACoreSwitch()
                egSwitchID = self._randomSelectACoreSwitch()
            # ingress = sfc.directions[0]['ingress']
            # egress = sfc.directions[0]['egress']
            # ingSwitch = self._dib.getConnectedSwitch(ingress.getServerID(),
            #     self.zoneName)
            # ingSwitchID = ingSwitch.switchID
            # egSwitch = self._dib.getConnectedSwitch(egress.getServerID(),
            #     self.zoneName)
            # egSwitchID = egSwitch.switchID
            self.requestIngSwitchID[rIndex] = ingSwitchID
            self.requestEgSwitchID[rIndex] = egSwitchID

    def _randomSelectACoreSwitch(self):
        coreSwitchNum = math.pow(self.podNum/2, 2)
        coreSwitchPerPod = math.floor(coreSwitchNum/self.podNum)
        # get core switch range
        minCoreSwitchIdx = self.minPodIdx * coreSwitchPerPod
        maxCoreSwitchIdx = minCoreSwitchIdx + coreSwitchPerPod * (self.maxPodIdx - self.minPodIdx + 1) - 1
        coreSwitchID = random.randint(minCoreSwitchIdx, maxCoreSwitchIdx)
        return coreSwitchID

    def _genPathLinkVar(self, rIndex):
        request = self.requestList[rIndex]
        sfc = self.getSFC4Request(request)
        vnfSeq = sfc.vNFTypeSequence
        # self.logger.info("vnfSeq: {0}".format(vnfSeq))
        for vnfIndex in range(len(vnfSeq)+1):
            for srcID, dstID in self.physicalLink:
                # self.logger.info("debug, _pathLinkVar rIndx:{0}".format(rIndex))
                self._pathLinkVar[rIndex, vnfIndex, srcID, dstID] = 1

    def _genVNFNodeVar(self, rIndex):
        request = self.requestList[rIndex]
        sfc = self.getSFC4Request(request)
        vnfSeq = sfc.vNFTypeSequence
        for vnfIndex in range(len(vnfSeq)+1):
            for switchID in self.switches:
                self._vnfDeployVar[rIndex, vnfIndex, switchID] = 1

    def _genVNFResConsume(self, rIndex):
        request = self.requestList[rIndex]
        sfc = self.getSFC4Request(request)
        trafficDemand = sfc.getSFCTrafficDemand()
        vnfSeq = sfc.vNFTypeSequence
        pM = PerformanceModel()
        for vnfIndex in range(len(vnfSeq)+1):
            for switchID in self.switches:
                if vnfIndex == len(vnfSeq):
                    self._resConsumeCoeff[rIndex, vnfIndex, switchID] = 0
                else:
                    vnfType = vnfSeq[vnfIndex]
                    coreConsume = pM.getExpectedServerResource(vnfType, 
                        trafficDemand)[0]
                    self._resConsumeCoeff[rIndex, vnfIndex,
                        switchID] = coreConsume

    def _trans2ILP(self):
        self.phi = {}
        self.a = {}
        # self.logger.info("pathlinkvar rindxs: {0}".format(self._pathLinkVar.keys()))
        self.logger.info("starting trans to ILP!")
        try:
            self.model.dispose()

            # Create optimization model
            self.model = gp.Model('netSolverILP')

            # timeout setting
            self.model.setParam('TimeLimit', 4000)

            # Create continuous variables
            self.phi = self.model.addVars(
                    self._pathLinkVar,
                    vtype=GRB.CONTINUOUS, name="flow", lb=0.0, ub=1.0)

            self.a = self.model.addVars(
                    self._vnfDeployVar,
                    vtype=GRB.BINARY, name="deploy", lb=0.0, ub=1.0)

            # add constraints
            for rIndex in range(len(self.requestList)):
                self.logger.info("add constr for rIndex:{0}".format(rIndex))
                egSwitchID = self.requestEgSwitchID[rIndex]

                request = self.requestList[rIndex]                
                sfc = self.getSFC4Request(request)
                vnfSeq = sfc.vNFTypeSequence

                # Flow-conservation constraints
                self.model.addConstrs(
                    (   self.phi.sum(rIndex, 0, switchID, '*') - self.phi.sum(rIndex, 0, '*', switchID) \
                        + self.a.sum(rIndex, 0, switchID) == 1
                        for switchID in self.switches if switchID == self.requestIngSwitchID[rIndex]
                        ), "srcNode_{0}".format(rIndex))

                self.model.addConstrs(
                    (   self.phi.sum(rIndex, 0, switchID, '*') - self.phi.sum(rIndex, 0, '*', switchID) \
                        + self.a.sum(rIndex, 0, switchID) == 0
                        for switchID in self.switches if switchID != self.requestIngSwitchID[rIndex]
                        ), "srcNode_{0}".format(rIndex))

                self.model.addConstrs(
                    (   self.phi.sum(rIndex, vnfIndex, switchID, '*') - self.phi.sum(rIndex, vnfIndex, '*', switchID) \
                        + self.a.sum(rIndex, vnfIndex, switchID) - self.a.sum(rIndex, vnfIndex-1, switchID) == 0
                        for switchID in self.switches
                        for vnfIndex in range(1, len(vnfSeq)+1)
                    ), "middleNode_{0}".format(rIndex))

                # fixed dst node
                self.model.addConstrs(
                    (   
                        self.a.sum(rIndex, len(vnfSeq), switchID) == 1
                        for switchID in self.switches if switchID == egSwitchID
                    ), "dstNode_{0}".format(rIndex))

                # exactly one node to deploy an vnf
                self.model.addConstrs(
                    (   
                        self.a.sum(rIndex, vnfIndex, '*') == 1
                        for vnfIndex in range(len(vnfSeq))
                    ), "vnfUnSplittable_{0}".format(rIndex))

                # NPoP provide correspoing vnf
                self.model.addConstrs(
                    (   
                        self.a.sum(rIndex, vnfIndex, [switchID for switchID in self.switches
                            if (vnfSeq[vnfIndex] in self._dib.getSwitch(switchID, self.zoneName).supportVNF) ]
                            ) == 1
                        for vnfIndex in range(len(vnfSeq))
                    ), "vnfDeployable_{0}".format(rIndex))

            # node capacity constraints
            self.logger.info("add node capacity constraints")
            nodeCapExpr = {}
            for switchID in self.switches:
                if switchID not in nodeCapExpr.keys():
                    nodeCapExpr[switchID] = LinExpr()
                for rIndex in range(len(self.requestList)):
                    nodeCapExpr[switchID] += self.a.prod(self._resConsumeCoeff, rIndex, '*', switchID)
            self.model.addConstrs(
                (   nodeCapExpr[switchID]  <= self.switchCapacity[switchID]
                    for switchID in self.switches
                ), "nodeCapacity")

            # link capacity constraints
            self.logger.info("add link capacity constraints")
            linkCapExpr = {}
            for srcID, dstID in self.physicalLink:
                if (srcID, dstID) not in linkCapExpr.keys():
                    linkCapExpr[srcID, dstID] = LinExpr()
                for rIndex in range(len(self.requestList)):
                    linkCapExpr[srcID, dstID] += self.phi.sum(rIndex, '*', srcID, dstID) * self._getTrafficDemand(rIndex)
            self.model.addConstrs(
                (   linkCapExpr[srcID, dstID]  <= self.linkCapacity[srcID, dstID]
                    for srcID, dstID in self.physicalLink
                ), "linkCapacity")

            self.logger.info("add constr finish!")

            # Add model obj
            self.model.setObjective(0, GRB.MINIMIZE)
            self.model.update()
            mkdirs("./NetSolverILP/")
            self.model.write("./NetSolverILP/netSolverILP.lp")

        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex)
            raise ValueError("gurobipy error")

        finally:
            pass

    def _getTrafficDemand(self, rIndex):
        request = self.requestList[rIndex]
        sfc = self.getSFC4Request(request)
        trafficDemand = sfc.getSFCTrafficDemand()
        return trafficDemand

    def solve(self):
        try:
            self.logger.info("gurobi start solve model!")
            self.model.optimize()

            # Print solution
            if self.model.status == GRB.OPTIMAL:
                self.logger.info("Find optimal solution!")
                # self._saveSolution()
            elif self.model.status == GRB.SUBOPTIMAL:
                self.logger.warning("model status: suboptimal")
            elif self.model.status == GRB.INFEASIBLE:
                self._tackleInfeasibleModel()
                # self._saveSolution()
            elif self.model.status in (GRB.INF_OR_UNBD, GRB.UNBOUNDED):
                self.logger.error('The relaxed model cannot be solved '
                    'because it is unbounded')
                raise ValueError('The relaxed model cannot be solved '
                    'because it is unbounded')
            else:
                self.logger.warning("unknown model status:{0}".format(self.model.status))
                raise ValueError("Partial ILP/ unknown model status")

        except Exception as ex:
            self.logger.error('Error reported')
            ExceptionProcessor(self.logger).logException(ex)

        finally:
            # don't clean up gruobi environment and model
            pass

    def _tackleInfeasibleModel(self):
        self.logger.warning("netSolverILP infeasible model")
        self.model.computeIIS()
        self.model.write("./NetSolverILP/netSolverILPIIS.ilp")

        # # Relax the constraints to make the model feasible
        # self.logger.debug('The model is infeasible; relaxing the constraints')
        # originNumVars = self.model.NumVars
        # self.model.feasRelaxS(0, False, False, True)

        # # More complext relax process
        # # originVars = self.model.getVars()
        # # ubpen = [1.0]*originNumVars
        # # constrs = self.getCapacityRelatedConstraintsFromIIS()
        # # if constrs == []:
        # #     raise ValueError("Invalid relaxed model's constrs.")
        # # self.model.feasRelax(0, False, originVars, None, ubpen, constrs, None)

        # # IntegralityFocus setting
        # # self.model.setParam('IntegralityFocus', 1)
        # self.model.setParam('TimeLimit', 3000)
        # self.model.optimize()

        # if self.model.status in (GRB.INF_OR_UNBD, GRB.INFEASIBLE, GRB.UNBOUNDED):
        #     self.logger.error('The relaxed model cannot be solved '
        #         'because it is infeasible {0} or unbounded {1}'
        #         ' or GRB.INF_OR_UNBD {2}'.format(
        #             GRB.INFEASIBLE, GRB.UNBOUNDED, GRB.INF_OR_UNBD
        #         ))
        #     raise ValueError('The relaxed model cannot be solved '
        #         'because it is infeasible or unbounded')

        # if self.model.status != GRB.OPTIMAL:
        #     self.logger.error('Optimization was stopped with '
        #         'status {0}'.format(self.model.status))
        #     raise ValueError('Optimization was stopped with '
        #         'status {0}'.format(self.model.status))

        # self.logger.debug('Slack values:')
        # slacks = self.model.getVars()[originNumVars:]
        # for sv in slacks:
        #     if sv.X > 1e-6:
        #         self.logger.debug('{0} = {1}'.format(sv.VarName, sv.X))

    # def getCapacityRelatedConstraintsFromIIS(self):
    #     relatedConstrs = []
    #     for c in self.model.getConstrs():
    #         self.logger.debug("c.IISConstr:{0},"
    #             "c.constrName{1}".format(c.IISConstr,
    #                                         c.constrName))
    #         if c.IISConstr and self.isRelated2Capacity(c.constrName):
    #             self.logger.warning("constraint {0}".format(c.constrName))
    #             relatedConstrs.append(c)
    #     return relatedConstrs

    # def isRelated2Capacity(self, constrName):
    #     if constrName.find("apacity") != -1:
    #         return True
    #     else:
    #         return False

    def getForwardingPathSetsDict(self):
        self.forwardingPathSetsDict = {}
        for rIndex in range(len(self.requestList)):
            mappingType = MAPPING_TYPE_NETSOLVER_ILP
            self.forwardingPathSetsDict[rIndex] = ForwardingPathSet(
                None, mappingType,
                None)

        return self.forwardingPathSetsDict

    def _updateResource(self):
        self.logger.info("_updateResource!")

        # update link residual bandwidth
        pathSolutions = self.model.getAttr('x', self.phi)
        # pathSolutions = self.phi.select('*','*','*')
        # for v in l.values():
        #     print("{}: {}".format(v.varName, v.X))
        for varName, value in pathSolutions.items():
            if value > 0:
                (rIndex, ingSwitchID, egSwitchID) = self._parsePathSolutionVar(varName)
                trafficDemand = self._getTrafficDemand(rIndex)
                self._dib.reserveLinkResource(ingSwitchID, egSwitchID, trafficDemand, self.zoneName)

        # update node residual resource
        vnfSolutions = self.model.getAttr('x', self.a)
        for varName, value in vnfSolutions.items():
            if value > 1 - (1e-3):
                (rIndex, vnfIndex, switchID) = self._parseVNFSolutionVar(varName)
                trafficDemand = self._getTrafficDemand(rIndex)
                reservedCores = self._resConsumeCoeff[rIndex, vnfIndex, switchID]
                reservedMemory = 0
                reservedBandwidth = trafficDemand
                expectedResource = (reservedCores, reservedMemory, reservedBandwidth)
                servers = self._dib.getConnectedNFVIs(switchID, self.zoneName)
                for server in servers:
                    serverID = server.getServerID()
                    if self._dib.hasEnoughServerResources(serverID, expectedResource, self.zoneName):
                        self._dib.reserveServerResources(serverID, reservedCores, reservedMemory,
                                                        trafficDemand, self.zoneName)
                        break
        self.logger.info("Update Resource successful!")

    def _parsePathSolutionVar(self, varName):
        # self.logger.info("varName:{0}".format(varName))
        rIndex = varName[0]
        vnfSeqStr = varName[1]
        ingSwitchID = varName[2]
        egSwitchID = varName[3]
        return (rIndex, ingSwitchID, egSwitchID)

    def _parseVNFSolutionVar(self, varName):
        # self.logger.info("varName:{0}".format(varName))
        rIndex = varName[0]
        vnfIndex = varName[1]
        switchID = varName[2]
        return (rIndex, vnfIndex, switchID)

    def _saveSolution(self):
        self.logger.error("Unimplemenation _saveSolution() !")
        # Print solution
        # if self.model.status == GRB.OPTIMAL:
        #     self.logger.info('Optimal Obj = {0}'.format(self.model.objVal))

        #     self.yVarSolution = self.model.getAttr('x', self.model)
        #     for yKey, value in self.yVarSolution.items():
        #         (rIndex, ingSwitchID, egSwitchID,
        #             vnfSeqStr, pathIndex) = yKey
        #         if value > 0:
        #             self.logger.info("modelYVar rIndex:{0}, {1}->{2}, c:{3}" \
        #                 "pathIndex:{4}, p/b:{5}. value={6}".format(rIndex,
        #                     ingSwitchID, egSwitchID, vnfSeqStr,
        #                     pathIndex, value))
        # elif self.model.status == GRB.SUBOPTIMAL:
        #     self.logger.warning("model status: suboptimal")
        # elif self.model.status == GRB.INFEASIBLE:
        #     self.logger.warning("infeasible model")
        #     self.model.computeIIS()
        #     self.model.write("./NetSolverILP/netSolverILPIIS.ilp")
        #     raise ValueError("infeasible model")
        # else:
        #     self.logger.warning("unknown model status:{0}".format(
        #         self.model.status))
        #     raise ValueError("unknown model status:{0}".format(
        #         self.model.status))

    def garbageCollector(self):
        self.model.dispose()
        self.env.dispose()
        self.logger.info("Garbage collect successful!")
