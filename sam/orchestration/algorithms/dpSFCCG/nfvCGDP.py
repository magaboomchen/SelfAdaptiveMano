#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
 dedicated protection sfc mapping
[2018][icc]Resource Requirements for
Reliable Service Function Chaining

column generation model
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


class NFVCGDedicatedProtection(OPRandomizedRoundingAlgorithm):
    def __init__(self, dib, requestList):
        self._dib = dib
        self.requestList = requestList

        logConfigur = LoggerConfigurator(__name__,
            './log', 'NFVCGDedicatedProtection.log', level='debug')
        self.logger = logConfigur.getLogger()

    def initRMP(self):
        self._initEnvModel()
        self._genInitialConfigurations()

    def updateRMP(self):
        self._genVariablesAndConsts()
        self._trans2LP()

    def _initEnvModel(self):
        self.env = gp.Env()
        self.cgModel = gp.Model('nfvCGDP', self.env)

    def _genInitialConfigurations(self):
        self.configurations = {}
        for request in self.requestList:
            self.request = request
            self.zoneName = request.attributes['zone']
            sdc = self._getSDC(request)
            if sdc not in self.configurations.keys():
                self.configurations[sdc] = []
                # (initPrimaryPath, initBackupPath) \
                #     = self._try2GenerateInitialSolution(sdc)
                initialSolutionsList = self._try2GenerateInitialSolution(sdc)
                # Don't update resource now!
                # self._updateResource4NFVCGDPInitPath(
                #     self._dividePath(initPrimaryPath))
                # self._updateResource4NFVCGDPInitPath(
                #     self._dividePath(initBackupPath))
                self.logger.debug(
                    "requestID:{0}, initial solutions:{1}".format(
                        self.request.requestID, initialSolutionsList))
                self.configurations[sdc].extend(initialSolutionsList)

    def _try2GenerateInitialSolution(self, sdc):
        maxTryNum = INITIAL_PATH_PER_REQUEST_NUM
        solutionList = []

        try:
            initPrimaryPath = self._genInitPrimaryPaths(sdc,
                WEIGHT_TYPE_PROPAGATION_DELAY_MODEL)
            initBackupPath = self._genInitBackupPaths(sdc,
                initPrimaryPath, WEIGHT_TYPE_PROPAGATION_DELAY_MODEL)
            solutionList.extend([initPrimaryPath, initBackupPath])
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex)
        maxTryNum = maxTryNum - 1

        while maxTryNum > 0:
            try:
                initPrimaryPath = self._genInitPrimaryPaths(sdc,
                    WEIGHT_TYPE_01_UNIFORAM_MODEL)
                initBackupPath = self._genInitBackupPaths(sdc,
                    initPrimaryPath, WEIGHT_TYPE_01_UNIFORAM_MODEL)
                solutionList.extend([initPrimaryPath, initBackupPath])
            except Exception as ex:
                ExceptionProcessor(self.logger).logException(ex)
            maxTryNum = maxTryNum - 1

        if solutionList == []:
            raise ValueError("Compute initial solution failed!")

        return solutionList

    def _genInitPrimaryPaths(self, sdc, weightType):
        mlg = MultiLayerGraph()
        mlg.loadInstance4dibAndRequest(self._dib, self.request,
            weightType)
        # WEIGHT_TYPE_0100_UNIFORAM_MODEL)
        # WEIGHT_TYPE_PROPAGATION_DELAY_MODEL)
        mlg.trans2MLG()
        (ingSwitchID, egSwitchID, vnfSeqStr) = sdc
        primaryPath = mlg.getPath(0, ingSwitchID, 
            self.getvnfSeqStrLength(vnfSeqStr), egSwitchID)
        self.logger.debug("primaryPath:{0}".format(primaryPath))
        return primaryPath

    def _genInitBackupPaths(self, sdc, initPrimaryPath, weightType):
        self.logger.debug("initPrimaryPath:{0}".format(initPrimaryPath))
        mlg = MultiLayerGraph()
        mlg.loadInstance4dibAndRequest(self._dib, self.request,
            weightType)
        # WEIGHT_TYPE_0100_UNIFORAM_MODEL)
        # WEIGHT_TYPE_PROPAGATION_DELAY_MODEL)
        abandonLinkIDList = self._getLinkID4Path(initPrimaryPath)
        self.logger.debug("abandonLinkIDList:{0}".format(
            abandonLinkIDList))
        mlg.addAbandonLinkIDs(abandonLinkIDList)
        mlg.trans2MLG()
        (ingSwitchID, egSwitchID, vnfSeqStr) = sdc
        backupPath = mlg.getPath(0, ingSwitchID,
            self.getvnfSeqStrLength(vnfSeqStr), egSwitchID)
        self.logger.debug("backupPath:{0}".format(backupPath))
        return backupPath

    def _getLinkID4Path(self, initPrimaryPath):
        # print(initPrimaryPath)
        # input [(0, 13), (1, 13), (1, 5), (1, 2), (1, 11), (1, 19)]
        linkIDList = []
        for index in range(len(initPrimaryPath)-1):
            srcNodeID = initPrimaryPath[index][1]
            dstNodeID = initPrimaryPath[index+1][1]
            if (srcNodeID != dstNodeID
                    and (srcNodeID, dstNodeID) not in linkIDList):
                linkIDList.append((srcNodeID, dstNodeID))
                linkIDList.append((dstNodeID, srcNodeID))
        return linkIDList

    def _genVariablesAndConsts(self):
        self._genPathLength()
        self._genTrafficDemand()
        self._genYVar()
        self._genPathLinkVar()
        self._genAVar()
        self._genPhysicalLink()
        self._genSwitch()
        self._genRequestVNFResConsum() # {[rIndex, f] : cpu cores}
        self._genEdgeDisjointCoeff()
        self._genlinkCapacityCoeff()
        self._genNodeCapacityCoeff()

    def _genPathLength(self):
        # Len: pi
        # pi: (s, d, vnfSeqStr)
        self.pathLength = {}
        for sdc, pathList in self.configurations.items():
            for pathIndex in range(len(pathList)):
                path = pathList[pathIndex]
                # self.logger.debug("path:{0}".format(path))
                (ingSwitchID, egSwitchID, vnfSeqStr) = sdc
                self.pathLength[ingSwitchID, egSwitchID,
                    vnfSeqStr, pathIndex] = len(path) - 1
        # self.logger.debug("pathLength:{0}".format(self.pathLength))

    def _genTrafficDemand(self):
        # D: rIndex, c, sd
        self.trafficDemand = {}
        for rIndex in range(len(self.requestList)):
            request = self.requestList[rIndex]
            sdc = self._getSDC(request)
            (ingSwitchID, egSwitchID, vnfSeqStr) = sdc
            sfc = self.getSFC4Request(request)
            self.trafficDemand[(rIndex, ingSwitchID, egSwitchID,
                vnfSeqStr)] = sfc.getSFCTrafficDemand()
        # self.logger.debug("self.trafficDemand:{0}".format(
        #     self.trafficDemand))

    def _genYVar(self):
        # y: rIndex, c, sd, pi, p/b
        self.yVar = {}
        for rIndex in range(len(self.requestList)):
            request = self.requestList[rIndex]
            ingSwitchID = self.getIngSwitchID4Request(request)
            egSwitchID = self.getEgSwitchID4Request(request)
            sfc = self.getSFC4Request(request)
            vnfSeqStr = self.vnfSeqList2Str(sfc.vNFTypeSequence)
            pathList = self.configurations[ingSwitchID, egSwitchID, vnfSeqStr]
            for pathIndex in range(len(pathList)):
                self.yVar[(rIndex, ingSwitchID, egSwitchID, vnfSeqStr,
                    pathIndex, 'p')] = 0
                self.yVar[(rIndex, ingSwitchID, egSwitchID, vnfSeqStr,
                    pathIndex, 'b')] = 0
        # self.logger.debug("self.yVar:{0}".format(self.yVar))

    def _genPathLinkVar(self):
        # delta: pi, link
        self.pathLinkVar = {}
        for sdc, pathList in self.configurations.items():
            (ingSwitchID, egSwitchID, vnfSeqStr) = sdc
            for pathIndex in range(len(pathList)):
                self._initPathLinkVar(sdc, pathIndex)
                path = pathList[pathIndex]
                linkIDList = self._getLinkIDList4ForwardingPath(path)
                for linkID in linkIDList:
                    (srcID, dstID) = linkID
                    self.pathLinkVar[(ingSwitchID, egSwitchID, vnfSeqStr,
                        pathIndex, srcID, dstID)] = 1
                    self.pathLinkVar[(ingSwitchID, egSwitchID, vnfSeqStr,
                        pathIndex, dstID, srcID)] = 1
        # self.logger.debug("self.pathLinkVar:{0}".format(
        #     self.pathLinkVar))

    def _initPathLinkVar(self, sdc, pathIndex):
        (ingSwitchID, egSwitchID, vnfSeqStr) = sdc
        linksInfoDict = self._dib.getLinksByZone(self.zoneName)
        for linkInfoDict in linksInfoDict.itervalues():
            link = linkInfoDict['link']
            srcID = link.srcID
            dstID = link.dstID
            self.pathLinkVar[(ingSwitchID, egSwitchID, vnfSeqStr,
                pathIndex, srcID, dstID)] = 0

    def _getLinkIDList4ForwardingPath(self, path):
        # input [(0, 13), (1, 13), (1, 5), (1, 2), (1, 11), (1, 19)]
        # return [(13, 5), (5, 2), (2, 11), (11, 19)]
        self.logger.debug("path:{0}".format(path))
        linkIDList = []
        for index in range(len(path)-1):
            srcLayerNum = path[index][0]
            srcID = path[index][1]
            dstLayerNum = path[index+1][0]
            dstID = path[index+1][1]
            if srcLayerNum == dstLayerNum:
                linkIDList.append((srcID, dstID))
        return linkIDList

    def _genEdgeDisjointCoeff(self):
        self.edgeDisjointCoeff = {}
        for key in self.yVar.keys():
            (rIndex, ingSwitchID, egSwitchID, vnfSeqStr, pathIndex, pb) = key

            pathLinkVarKeyList = [pathLinkVarKey 
                for pathLinkVarKey in self.pathLinkVar.keys()
                if (pathLinkVarKey[0] == ingSwitchID
                and pathLinkVarKey[1] == egSwitchID
                and pathLinkVarKey[2] == vnfSeqStr
                and pathLinkVarKey[3] == pathIndex)]

            for pathLinkVarKey in pathLinkVarKeyList:
                srcID = pathLinkVarKey[4]
                dstID = pathLinkVarKey[5]
                if (srcID, dstID) not in self.edgeDisjointCoeff.keys():
                    self.edgeDisjointCoeff[srcID, dstID] = {}
                if (dstID, srcID) not in self.edgeDisjointCoeff.keys():
                    self.edgeDisjointCoeff[dstID, srcID] = {}
                pathLinkVar = self.pathLinkVar[(ingSwitchID, egSwitchID,
                    vnfSeqStr, pathIndex, srcID, dstID)]
                if srcID > dstID:
                    self.edgeDisjointCoeff[dstID, srcID][rIndex, ingSwitchID,
                        egSwitchID, vnfSeqStr, pathIndex, pb] = pathLinkVar
                else:
                    self.edgeDisjointCoeff[srcID, dstID][rIndex, ingSwitchID,
                        egSwitchID, vnfSeqStr, pathIndex, pb] = pathLinkVar
        # self.logger.debug("self.edgeDisjointCoeff:{0}".format(
        #     self.edgeDisjointCoeff))

    def _genlinkCapacityCoeff(self):
        self.linkCapacityCoeff = {}
        for key in self.yVar.keys():
            (rIndex, ingSwitchID, egSwitchID, vnfSeqStr, pathIndex, pb) = key

            pathLinkVarKeyList = [pathLinkVarKey 
                for pathLinkVarKey in self.pathLinkVar.keys()
                if (pathLinkVarKey[0] == ingSwitchID
                and pathLinkVarKey[1] == egSwitchID
                and pathLinkVarKey[2] == vnfSeqStr
                and pathLinkVarKey[3] == pathIndex) ]

            for pathLinkVarKey in pathLinkVarKeyList:
                srcID = pathLinkVarKey[4]
                dstID = pathLinkVarKey[5]
                if (srcID, dstID) not in self.linkCapacityCoeff.keys():
                    self.linkCapacityCoeff[srcID, dstID] = {}
                pathLinkVar = self.pathLinkVar[(ingSwitchID, egSwitchID, vnfSeqStr,
                    pathIndex, srcID, dstID)]
                trafficDemand = self.trafficDemand[(rIndex, ingSwitchID, egSwitchID,
                    vnfSeqStr)]
                self.linkCapacityCoeff[srcID, dstID][rIndex, ingSwitchID,
                    egSwitchID, vnfSeqStr, pathIndex, pb] = pathLinkVar * trafficDemand
        # self.logger.debug("self.linkCapacityCoeff:{0}".format(
        #     self.linkCapacityCoeff))

    def _genNodeCapacityCoeff(self):
        self.nodeCapacityCoeff = {}

        for key in self.yVar.keys():
            (rIndex, ingSwitchID, egSwitchID, vnfSeqStr, pathIndex, pb) = key

            vnfSeqList = self.vnfSeqStr2List(vnfSeqStr)

            for switchID in self.switches:
                if switchID not in self.nodeCapacityCoeff.keys():
                    self.nodeCapacityCoeff[switchID] = {}
                resConsumeInThisSwitch = 0
                for vnfType in vnfSeqList:
                    if self.aVar[ingSwitchID, egSwitchID, vnfSeqStr,
                            pathIndex, vnfType, switchID] == 1:
                        resConsume = self.requestVNFServerRes[(rIndex,
                            ingSwitchID, egSwitchID, vnfSeqStr, vnfType)]
                        resConsumeInThisSwitch = resConsumeInThisSwitch \
                            + resConsume

                self.nodeCapacityCoeff[switchID][rIndex, ingSwitchID,
                        egSwitchID, vnfSeqStr,
                        pathIndex, pb] = resConsumeInThisSwitch
        # self.logger.debug("self.nodeCapacityCoeff:{0}".format(
        #     self.nodeCapacityCoeff))

    def _genAVar(self):
        # a: f, v, pi
        self.aVar = {}
        for sdc, pathList in self.configurations.items():
            (ingSwitchID, egSwitchID, vnfSeqStr) = sdc
            for pathIndex in range(len(pathList)):
                self._initAVar(sdc, pathIndex)
                path = pathList[pathIndex]
                for index in range(len(path)-1):
                    (currentNodeLayerNum, currentNodeID) = path[index]
                    (nextNodeLayerNum, nextNodeID) = path[index+1]
                    if currentNodeLayerNum != nextNodeLayerNum:
                        vnfSeqList = self.vnfSeqStr2List(vnfSeqStr)
                        vnfType = vnfSeqList[currentNodeLayerNum]
                        self.aVar[(ingSwitchID, egSwitchID, vnfSeqStr, 
                            pathIndex, vnfType, currentNodeID)] = 1
        # self.logger.debug("aVar.keys:{0}".format(self.aVar.keys()))

    def _initAVar(self, sdc, pathIndex):
        (ingSwitchID, egSwitchID, vnfSeqStr) = sdc
        linksInfoDict = self._dib.getLinksByZone(self.zoneName)
        for linkInfoDict in linksInfoDict.itervalues():
            link = linkInfoDict['link']
            srcID = link.srcID
            dstID = link.dstID
            for vnfType in range(-1, VNF_TYPE_MAX):
                self.aVar[(ingSwitchID, egSwitchID, vnfSeqStr, 
                    pathIndex, vnfType, dstID)] = 0

    def _genPhysicalLink(self):
        # cap: link
        self.links = {}
        for key in self._dib.getLinksByZone(self.zoneName).keys():
            (srcNodeID, dstNodeID) = key
            if (self._dib.isServerID(srcNodeID) 
                    or self._dib.isServerID(dstNodeID)):
                continue
            self.links[(srcNodeID, dstNodeID)] \
                = self._dib.getLinkResidualResource(
                    srcNodeID, dstNodeID, self.zoneName)
            
            # if self.links[(srcNodeID, dstNodeID)] < 1 :
            #     self.logger.debug("capacity:{0}".format(
            #         self.links[(srcNodeID, dstNodeID)]
            #     ))
            #     raw_input()

        self.physicalLink , self.linkCapacity = gp.multidict(self.links)

        # for link,capacity in self.linkCapacity.items():
        #     if capacity < 1:
        #         self.logger.debug("nfvCGDP, link:{0}, capacity:{1}".format(
        #             link, capacity))
        #         raw_input()

        # self.logger.debug("phsicalLink:{0}, self.linkCapacity:{1}".format(
        #     self.physicalLink, self.linkCapacity))

    def _genSwitch(self):
        # cap: vNode
        self.switches = {}
        for switchID, switchInfoDict in self._dib.getSwitchesByZone(
                self.zoneName).items():
            switch = switchInfoDict['switch']
            self.switches[switchID] = [self._dib.getNPoPServersCapacity(
                switchID, self.zoneName)]
        self.switches, self.switchCapacity = gp.multidict(self.switches)
        # self.logger.debug("switches:{0}".format(self.switches))

    def _genRequestVNFResConsum(self):
        # deprecated delta: f
        # vnfRes: rIndex, sd, c, f
        self.requestVNFServerRes = {}
        for rIndex in range(len(self.requestList)):
            request = self.requestList[rIndex]
            for sdc, pathList in self.configurations.items():
                (ingSwitchID, egSwitchID, vnfSeqStr) = sdc
                vnfSeqList = self.vnfSeqStr2List(vnfSeqStr)
                for vnfType in vnfSeqList:
                    sfc = self.getSFC4Request(request)
                    trafficDemand = sfc.getSFCTrafficDemand()
                    pM = PerformanceModel()
                    coreConsume = pM.getExpectedServerResource(vnfType, 
                        trafficDemand)[0]
                    self.requestVNFServerRes[(rIndex, ingSwitchID, egSwitchID,
                        vnfSeqStr, vnfType)] = coreConsume
        # self.logger.debug("self.requestVNFServerRes:{0}".format(
        #     self.requestVNFServerRes))

    def _trans2LP(self):
        try:
            self.cgModel.dispose()

            # Create optimization model
            self.cgModel = gp.Model('nfvCGDP')

            # timeout setting
            self.cgModel.setParam('TimeLimit', 1000)

            # Create continuous variables
            self.modelYVar = self.cgModel.addVars(self.yVar,
                vtype=GRB.CONTINUOUS, name="y", lb=0.0, ub=1.0)
            # yVar[(rIndex, ingSwitchID, egSwitchID, vnfSeqStr, pathIndex, 'b')] = 0

            # (10a) and (10b)
            self.cgModel.addConstrs(
                (   self.modelYVar.sum(rIndex, '*',
                    '*', '*', '*', pb) == 1
                    for rIndex in range(len(self.requestList))
                    for pb in ['p', 'b']
                    ), "pathNum")

            # edge disjoint (11)
            self.cgModel.addConstrs(
                (   self.modelYVar.prod(
                        self.edgeDisjointCoeff[srcID, dstID], rIndex, '*', 
                            '*', '*', '*', '*')  <= 1
                    for rIndex in range(len(self.requestList))
                    for srcID, dstID in self.physicalLink if srcID < dstID
                ), "edgeDisjoint")

            # link capacity (12)
            self.cgModel.addConstrs(
                (   self.modelYVar.prod(
                        self.linkCapacityCoeff[srcID, dstID], '*', '*', '*',
                            '*', '*', '*') <= self.linkCapacity[srcID, dstID]
                    for srcID, dstID in self.physicalLink
                ), "linkCapacity")

            # node capacity (13)
            self.cgModel.addConstrs(
                (   self.modelYVar.prod(self.nodeCapacityCoeff[switchID], '*',
                        '*', '*', '*', '*', '*') <= self.switchCapacity[switchID]
                    for switchID in self.switches
                ), "nodeCapacity")

            # Add model obj
            self._genModelObj()
            self.cgModel.setObjective(self.modelObj, GRB.MINIMIZE)
            self.cgModel.update()
            mkdirs("./LP/")
            self.cgModel.write("./LP/nfvCGDP.lp")

        # except GurobiError:
        #     self.logger.error('Error reported')

        except Exception as ex:
            self.logger.error('Error reported')
            ExceptionProcessor(self.logger).logException(ex)

        finally:
            pass

    def _genModelObj(self):
        self.modelObj = LinExpr()
        for key,value in self.yVar.items():
            (rIndex, ingSwitchID, egSwitchID,
                vnfSeqStr, pathIndex, pb) = key
            self.modelObj += self.trafficDemand[rIndex,
                    ingSwitchID, egSwitchID, vnfSeqStr] \
                * self.pathLength[ingSwitchID, egSwitchID,
                    vnfSeqStr, pathIndex] \
                * (self.modelYVar.sum(rIndex, ingSwitchID,
                    egSwitchID, vnfSeqStr, pathIndex, '*'))

    def solve(self):
        try:
            self.cgModel.optimize()

            # Print solution
            if self.cgModel.status == GRB.OPTIMAL:
                self._saveSolution()
            elif self.cgModel.status == GRB.SUBOPTIMAL:
                self.logger.warning("model status: suboptimal")
            elif self.cgModel.status == GRB.INFEASIBLE:
                self._tackleInfeasibleModel()
                self._saveSolution()
            elif self.cgModel.status in (GRB.INF_OR_UNBD, GRB.UNBOUNDED):
                self.logger.error('The relaxed model cannot be solved '
                    'because it is unbounded')
                raise ValueError('The relaxed model cannot be solved '
                    'because it is unbounded')
            else:
                self.logger.warning("unknown model status:{0}".format(self.cgModel.status))
                raise ValueError("Partial LP unknown model status")

        except Exception as ex:
            self.logger.error('Error reported')
            ExceptionProcessor(self.logger).logException(ex)

        finally:
            # don't clean up gruobi environment and model
            pass

    def _tackleInfeasibleModel(self):
        self.logger.warning("nfvCGDP infeasible model")
        self.cgModel.computeIIS()
        self.cgModel.write("./LP/nfvCGDPIIS.ilp")

        # Relax the constraints to make the model feasible
        self.logger.debug('The model is infeasible; relaxing the constraints')
        originNumVars = self.cgModel.NumVars
        self.cgModel.feasRelaxS(0, False, False, True)

        # More complext relax process
        # originVars = self.cgModel.getVars()
        # ubpen = [1.0]*originNumVars
        # constrs = self.getCapacityRelatedConstraintsFromIIS()
        # if constrs == []:
        #     raise ValueError("Invalid relaxed model's constrs.")
        # self.cgModel.feasRelax(0, False, originVars, None, ubpen, constrs, None)

        # IntegralityFocus setting
        self.cgModel.setParam('IntegralityFocus', 1)
        self.cgModel.setParam('TimeLimit', 3000)
        self.cgModel.optimize()

        if self.cgModel.status in (GRB.INF_OR_UNBD, GRB.INFEASIBLE, GRB.UNBOUNDED):
            self.logger.error('The relaxed model cannot be solved '
                'because it is infeasible {0} or unbounded {1}'
                ' or GRB.INF_OR_UNBD {2}'.format(
                    GRB.INFEASIBLE, GRB.UNBOUNDED, GRB.INF_OR_UNBD
                ))
            raise ValueError('The relaxed model cannot be solved '
                'because it is infeasible or unbounded')

        if self.cgModel.status != GRB.OPTIMAL:
            self.logger.error('Optimization was stopped with '
                'status {0}'.format(self.cgModel.status))
            raise ValueError('Optimization was stopped with '
                'status {0}'.format(self.cgModel.status))

        self.logger.debug('Slack values:')
        slacks = self.cgModel.getVars()[originNumVars:]
        for sv in slacks:
            if sv.X > 1e-6:
                self.logger.debug('{0} = {1}'.format(sv.VarName, sv.X))

    def getCapacityRelatedConstraintsFromIIS(self):
        relatedConstrs = []
        for c in self.cgModel.getConstrs():
            self.logger.debug("c.IISConstr:{0},"
                "c.constrName{1}".format(c.IISConstr,
                                            c.constrName))
            if c.IISConstr and self.isRelated2Capacity(c.constrName):
                self.logger.warning("constraint {0}".format(c.constrName))
                relatedConstrs.append(c)
        return relatedConstrs

    def isRelated2Capacity(self, constrName):
        if constrName.find("apacity") != -1:
            return True
        else:
            return False

    def getDualVariables(self):
        self._genDualVariables()
        # self._logDualVariables()
        return self.dualVars

    def _genDualVariables(self):
        # variable format
        # self.dualVars['constr10a'][rIndex, 'p']
        # self.dualVars['constr10b'][rIndex, 'b']
        # self.dualVars['constr11'][rIndex, srcID, dstID]
        # self.dualVars['constr12'][srcID, dstID]
        # self.dualVars['constr13'][switchID]
        self.dualVars = {}
        self._genDualVar10()
        self._genDualVar11()
        self._genDualVar12()
        self._genDualVar13()

    def _genDualVar10(self):
        self.dualVars['constr10a'] = {}
        self.dualVars['constr10b'] = {}
        for rIndex in range(len(self.requestList)):
            constr = self.cgModel.getConstrByName("pathNum[{0},p]".format(rIndex))
            self.dualVars['constr10a'][rIndex, 'p'] = self._getConstrDualVariable(
                constr)
            constr = self.cgModel.getConstrByName("pathNum[{0},b]".format(rIndex))
            self.dualVars['constr10b'][rIndex, 'b'] = self._getConstrDualVariable(
                constr)

    def _genDualVar11(self):
        self.dualVars['constr11'] = {}
        for rIndex in range(len(self.requestList)):
            for srcID, dstID in self.physicalLink:
                if srcID < dstID:
                    constr = self.cgModel.getConstrByName(
                        "edgeDisjoint[{0},{1},{2}]".format(
                            rIndex, srcID, dstID))
                    self.dualVars['constr11'][rIndex, srcID,
                        dstID] = self._getConstrDualVariable(constr)

    def _genDualVar12(self):
        self.dualVars['constr12'] = {}
        for srcID, dstID in self.physicalLink:
            constr = self.cgModel.getConstrByName(
                "linkCapacity[{0},{1}]".format(srcID, dstID))
            self.dualVars['constr12'][srcID,
                dstID] = self._getConstrDualVariable(constr)

    def _genDualVar13(self):
        self.dualVars['constr13'] = {}
        for switchID in self.switches:
            constr = self.cgModel.getConstrByName(
                "nodeCapacity[{0}]".format(switchID))
            self.dualVars['constr13'][switchID] \
                = self._getConstrDualVariable(constr)

    def _getConstrDualVariable(self, constr):
        return self.cgModel.getAttr(GRB.Attr.Pi, [constr])[0]

    def _logDualVariables(self):
        for key,value in self.dualVars.items():
            self.logger.debug("key:{0}".format(key))
            for valueIndex in value.keys():
                self.logger.debug("valueIndex:{0}".format(valueIndex))

    def addConfigurations(self, configurations):
        # configurations[sdc] = pathList
        for sdc in configurations.keys():
            pathList = configurations[sdc]
            self.configurations[sdc].extend(pathList)

    def hasNewConfigurations(self, configurations):
        for sdc in configurations.keys():
            pathList = configurations[sdc]
            for path in pathList:
                if path not in self.configurations[sdc]:
                    return True
        return False

    def transRMP2ILP(self):
        for key, variable in self.modelYVar.items():
            variable.vtype = GRB.BINARY

        # IntegralityFocus setting
        self.cgModel.setParam('IntegralityFocus', 1)

    def getSolutions(self):
        if (self.cgModel.status == GRB.OPTIMAL 
                or self.cgModel.status == GRB.SUBOPTIMAL):
            self.logger.info('Optimal Obj = {0}'.format(self.cgModel.objVal))
            self.yVarSolutions = self.cgModel.getAttr('x', self.modelYVar)
            return self.yVarSolutions
        else:
            return None

    def logUnZeroSolutionVar(self, solutions):
        self.logger.debug("logUnZeroSolutionVar:")
        for solution in solutions:
            if solution.X > 0:
                self.logger.debug("solution:{0}".format(solution))

    def getForwardingPathSetsDict(self):
        self.forwardingPathSetsDict = {}
        for rIndex in range(len(self.requestList)):
            primaryPathSolutions = self.modelYVar.select(rIndex,'*','*','*',
                                                            '*', 'p')
            for solution in primaryPathSolutions:
                # if solution.X == 1:
                if solution.X >= 1 - (1e-3):
                    (ingSwitchID, egSwitchID, vnfSeqStr, 
                        pathIndex) = self._getSolutionVarIndexTuple(solution)
                    sdc = (ingSwitchID, egSwitchID, vnfSeqStr)
                    primaryFP = self.configurations[sdc][pathIndex]
                    primaryFP = self._selectNPoPNodeAndServers(primaryFP,
                        rIndex)
                    primaryForwardingPath = {1:
                            primaryFP
                        }
                    break
            else:
                self.logUnZeroSolutionVar(primaryPathSolutions)
                # raise ValueError("Can't find primaryPathSolutions")
                self.logger.error("Can't find primaryPathSolutions, random selection")
                selectedIdx = randrange(len(primaryPathSolutions))
                for idx, solution in enumerate(primaryPathSolutions):
                    if idx != selectedIdx:
                        continue
                    else:
                        (ingSwitchID, egSwitchID, vnfSeqStr, pathIndex) \
                                = self._getSolutionVarIndexTuple(solution)
                        sdc = (ingSwitchID, egSwitchID, vnfSeqStr)
                        primaryFP = self.configurations[sdc][pathIndex]
                        primaryFP = self._selectNPoPNodeAndServers(primaryFP,
                            rIndex)
                        primaryForwardingPath = {1:
                                primaryFP
                            }
                        break

            abandonServers = self._getNFVIInPrimaryPath(primaryFP)

            backupPathSolutions = self.modelYVar.select(rIndex,'*','*','*',
                                                            '*', 'b')
            for solution in backupPathSolutions:
                if solution.X >= 1 - (1e-3):
                    (ingSwitchID, egSwitchID, vnfSeqStr, 
                        pathIndex) = self._getSolutionVarIndexTuple(solution)
                    sdc = (ingSwitchID, egSwitchID, vnfSeqStr)
                    backupFP = self.configurations[sdc][pathIndex]
                    backupFP = self._selectNPoPNodeAndServers(backupFP,
                        rIndex, abandonServers)
                    backupForwardingPath = {1:
                        {
                            (
                                ("repairMethod", "increaseBackupPathPrioriy")
                            ): backupFP
                        }        
                    }
                    break
            else:
                self.logUnZeroSolutionVar(backupPathSolutions)
                # raise ValueError("Can't find backupPathSolutions")
                self.logger.error("Can't find backupPathSolutions, random selection")
                selectedIdx = randrange(len(backupPathSolutions))
                for idx, solution in enumerate(backupPathSolutions):
                    if idx != selectedIdx:
                        continue
                    else:
                        (ingSwitchID, egSwitchID, vnfSeqStr, pathIndex) \
                                = self._getSolutionVarIndexTuple(solution)
                        sdc = (ingSwitchID, egSwitchID, vnfSeqStr)
                        backupFP = self.configurations[sdc][pathIndex]
                        backupFP = self._selectNPoPNodeAndServers(backupFP,
                            rIndex, abandonServers)
                        backupForwardingPath = {1:
                            {
                                (
                                    ("repairMethod", "increaseBackupPathPrioriy")
                                ): backupFP
                            }        
                        }
                        break

            mappingType = MAPPING_TYPE_E2EP
            self.forwardingPathSetsDict[rIndex] = ForwardingPathSet(
                primaryForwardingPath, mappingType,
                backupForwardingPath)

        return self.forwardingPathSetsDict

    def _getNFVIInPrimaryPath(self, primaryFP):
        serverList = []
        for segPath in primaryFP:
            layerNum, firstNodeID = segPath[0]
            layerNum, lastNodeID = segPath[-1]
            if firstNodeID not in serverList:
                serverList.extend([firstNodeID])
            if lastNodeID not in serverList:
                serverList.extend([lastNodeID])
        return serverList

    def _getSolutionVarIndexTuple(self, solution):
        varName = solution.VarName
        index1 = varName.find('[')
        index2 = varName.find(']')
        varIndice = varName[index1+1:index2]
        varIndiceList = varIndice.split(',')

        ingSwitchID = int(varIndiceList[1])
        egSwitchID = int(varIndiceList[2])
        vnfSeqStr = varIndiceList[3]
        pathIndex = int(varIndiceList[4])
        return (ingSwitchID, egSwitchID, vnfSeqStr, pathIndex)

    def _saveSolution(self):
        # Print solution
        if self.cgModel.status == GRB.OPTIMAL:
            self.logger.info('Optimal Obj = {0}'.format(self.cgModel.objVal))

            self.yVarSolution = self.cgModel.getAttr('x', self.modelYVar)
            for yKey, value in self.yVarSolution.items():
                (rIndex, ingSwitchID, egSwitchID,
                    vnfSeqStr, pathIndex, pb) = yKey
                if value > 0:
                    self.logger.info("modelYVar rIndex:{0}, {1}->{2}, c:{3}" \
                        "pathIndex:{4}, p/b:{5}. value={6}".format(rIndex,
                            ingSwitchID, egSwitchID, vnfSeqStr,
                            pathIndex, pb, value))
        elif self.cgModel.status == GRB.SUBOPTIMAL:
            self.logger.warning("model status: suboptimal")
        elif self.cgModel.status == GRB.INFEASIBLE:
            self.logger.warning("infeasible model")
            self.cgModel.computeIIS()
            self.cgModel.write("./LP/nfvCGDPIIS.ilp")
            raise ValueError("infeasible model")
        else:
            self.logger.warning("unknown model status:{0}".format(
                self.cgModel.status))
            raise ValueError("unknown model status:{0}".format(
                self.cgModel.status))

    def garbageCollector(self):
        self.cgModel.dispose()
        self.env.dispose()
