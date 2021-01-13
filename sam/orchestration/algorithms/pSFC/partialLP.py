#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
original sfc mapping
[2018][globecom]Partial Rerouting for High-Availability and
Low-Cost Service Function Chain
'''

import copy

import numpy as np
import gurobipy as gp
from gurobipy import GRB
from gurobipy import *

from sam.base.sfc import *
from sam.base.path import *
from sam.base.server import *
from sam.base.mkdirs import *
from sam.base.messageAgent import *
from sam.base.socketConverter import *
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.orchestration.algorithms.multiLayerGraph import *
from sam.orchestration.algorithms.performanceModel import *
from sam.orchestration.algorithms.oPSFC.originalPartialLP import *


class PartialLP(OriginalPartialLP):
    def __init__(self, dib, requestList, requestForwardingPathSet):
        self._dib = dib
        self.requestList = requestList
        self.requestForwardingPathSet = requestForwardingPathSet

        logConfigur = LoggerConfigurator(__name__,
            './log',
            'PartialLP.log', level='debug')
        self.logger = logConfigur.getLogger()

    def mapSFCI(self):
        self.logger.info("PartialLP mapSFCI")
        self._init()
        self._genVariablesAndConsts()
        self._trans2LPAndSolve()

    def _init(self):
        self.requestPartialPath = gp.tuplelist()   # [pIndex]
        self.requestPartialPathRIndex = {}  # {pIndex: rIndex}
        self.requestPartialPathBp = {}  # {pIndex: bp}
        self.requestPartialPathXp = {}  # {pIndex: tuple(Xp)}
        self.requestPartialPathSrcSwitchID = {} # {pIndex: sp}
        self.requestPartialPathDstSwitchID = {} # {pIndex: tp}
        self.requestPartialPathTrafficDemand = {}   # {pIndex: lp}

        self.virtualLink = {}   # {(pIndex, i, j): 1}

        self.partialPathVnf = {}    # {(pIndex, i): resourceConsumOfi(cpu)}

        self.switches = {}  # {switchID: NPoPCapacity}

        self.phsicalLink = gp.tuplelist()   # [(srcID, dstID)]
        self.linkCapacity = {}  # {(srcID, dstID): capacity}

        self.zoneName = self.requestList[0].attributes['zone']

    def _genVariablesAndConsts(self):
        # p = (sp, bp, tp, Xp, lp)
        self._genPartialPath()  # l_r, s_r, t_r
        # f^{p}_{i,j,u,v}
        # f^{p}_{0,mr,u,sr}
        self._genPhysicalLinksVar() # C_{u,v}
        self._genVirtualLinkVar()
        # A^p_{i,w}
        self._genSwitchesVar()  # C_w
        self._genVnfVar()

        self._genRequestLoad()

    def _genPartialPath(self):
        self.partialPath = {}
        for rIndex in range(len(self.requestList)):
            self._getPartialPathOfRequest(rIndex)
        
        if self.partialPath == {}:
            self.logger.warning("no partial paths at all.")
            raise ValueError("no partial paths at all.")

        (self.requestPartialPath, 
            self.requestPartialPathRIndex,
            self.requestPartialPathBp,
            self.requestPartialPathXp,
            self.requestPartialPathSrcSwitchID,
            self.requestPartialPathDstSwitchID,
            self.requestPartialPathTrafficDemand) = gp.multidict(self.partialPath)

    def _getPartialPathOfRequest(self, rIndex):
        request = self.requestList[rIndex]
        sfc = request.attributes['sfc']

        sffIDList = self._getSFFIDList(rIndex)  # sffIDList example: [(0,2),(1,3),(2,3),(4,10)]
        aggSFFIDList = self._getAggSFFIDList(sffIDList)   # aggSFFIDList example: [[(0,2)],[(1,3),(2,3)],[(4,10)]]
        for index in range(1, len(aggSFFIDList)-1):
            preAggSFF = aggSFFIDList[index-1]
            currentAggSFF = aggSFFIDList[index]
            nextAggSFF = aggSFFIDList[index+1]

            if not self._hasPartialPath(index, len(aggSFFIDList), preAggSFF, 
                                        currentAggSFF, nextAggSFF):
                self.logger.warning("has not any partial path")
                continue

            pIndex = self._assignPartialPathIndex()
            bpID = currentAggSFF[0][1]
            Xp = []
            for sff in currentAggSFF:
                layerNum = sff[0]
                vnfType = sfc.vNFTypeSequence[layerNum-1]
                Xp.append(vnfType)
            sp = preAggSFF[0][1]
            tp = nextAggSFF[0][1]
            lp = sfc.getSFCTrafficDemand()
            self.logger.debug("Xp in list:{0}".format(Xp))
            self.partialPath[pIndex] = (rIndex, bpID, tuple(Xp), sp, tp, lp)
        self.logger.debug("partialPath:{0}".format(self.partialPath))

    def _assignPartialPathIndex(self):
        return len(self.partialPath)

    def _getSFFIDList(self, rIndex):
        primaryPath = self._getPrimaryPath(rIndex)

        # [
        #  [(0, 10022), (0, 13), (0, 4), (0, 0), (0, 6), (0, 1), (0, 10), (0, 19), (0, 10008)],
        #  [(1, 10008), (1, 19), (1, 10008)],
        #  [(2, 10008), (2, 19), (2, 10008)],
        #  [(3, 10008), (3, 19), (3, 10028)]
        # ]

        sffIDList = []
        for segPath in primaryPath:
            sffID = segPath[1]
            sffIDList.append(sffID)
        if len(primaryPath[-1]) != 3:
            EgSFF = primaryPath[-1][-2]
            sffIDList.append(EgSFF)

        self.logger.debug("sffIDList:{0}".format(sffIDList))

        return sffIDList

    def _getAggSFFIDList(self, sffIDList):
        aggSFFIDList = [[sffIDList[0]]]

        currentPointer = 1
        while currentPointer < len(sffIDList)-1:
            # self.logger.debug("currentPointer:{0}".format(currentPointer))
            currentSFF = sffIDList[currentPointer]
            tmpList = [currentSFF]
            # self.logger.debug("currentSFF:{0}".format(currentSFF))
            movingPointer = currentPointer + 1
            findDifferentSFFFlag = False
            for movingPointer in range(currentPointer+1, len(sffIDList)-1):
                # self.logger.debug("movingPointer:{0}".format(movingPointer))
                movingPointerSFF = sffIDList[movingPointer]
                # self.logger.debug("movingPointerSFF:{0}".format(movingPointerSFF))
                if movingPointerSFF[1] == currentSFF[1]:
                    tmpList.append(movingPointerSFF)
                else:
                    findDifferentSFFFlag = True
                    break

            currentPointer = movingPointer
            aggSFFIDList.append(tmpList)

            # This function has a complicate condition
            # correctness needs to be proofed and test
            if ((movingPointer == len(sffIDList)-2
                and not findDifferentSFFFlag)
                or movingPointer > len(sffIDList)-2):
                break

        aggSFFIDList.append([sffIDList[-1]])

        self.logger.debug("aggSFFIDList:{0}".format(aggSFFIDList))

        return aggSFFIDList

    def _hasPartialPath(self, index, lenaggSFFIDList, preAggSFF,
                    currentAggSFF, nextAggSFF):
        preAggSFFID = preAggSFF[0][1]
        currentAggSFFID = currentAggSFF[0][1]
        nextAggSFFID = nextAggSFF[0][1]
        # self.logger.debug(
        #     "_hasPartialPath lenaggSFFIDList:{0} index: {1} preAggSFFID:{2} currentAggSFFID:{3} nextAggSFFID:{4}".format(
        #         lenaggSFFIDList, index, preAggSFFID, currentAggSFFID, nextAggSFFID
        #     ))
        if index == 1 and preAggSFFID == currentAggSFFID:
            return False

        if index == lenaggSFFIDList-2 and currentAggSFFID == nextAggSFFID:
            return False

        return True

    def _getPrimaryPath(self, rIndex):
        forwardingPathSet = self.requestForwardingPathSet[rIndex]
        self.logger.debug("forwardingPathSet:{0}".format(forwardingPathSet))

        primaryPath = forwardingPathSet.primaryForwardingPath[1]      
        self.logger.debug("primaryPath:{0}".format(primaryPath))

        return primaryPath

    def _genVirtualLinkVar(self):
        self.virtualLink = {}
        for partialPath, value in self.partialPath.items():  # [pIndex] = (rIndex, bpID, tuple(Xp), sp, tp, lp)
            pIndex = partialPath
            (rIndex, bpID, Xp, sp, tp, lp) = value
            m_r = Xp[0]
            n_r = Xp[-1]
            self.virtualLink[(pIndex, 0, m_r)] = 1
            self.virtualLink[(pIndex, n_r, -1)] = 1
            for index in range(len(Xp)-1):
                vnfI = Xp[index]
                vnfJ = Xp[index+1]
                self.virtualLink[(pIndex, vnfI, vnfJ)] = 1
        self.virtualLink, virtualLinkState = gp.multidict(self.virtualLink)
        self.logger.debug("virtualLink:{0}".format(self.virtualLink))

    def _genVnfVar(self):   # {(pIndex, vnfI): resourceConsumOfi(cpu)}
        self.partialPathVnf = {}
        for partialPath, value in self.partialPath.items():
            pIndex = partialPath
            (rIndex, bpID, Xp, sp, tp, lp) = value
            self.partialPathVnf[(pIndex, 0)] = 1
            self.partialPathVnf[(pIndex, -1)] = 1
            for index in range(len(Xp)):
                vnfI = Xp[index]
                pM = PerformanceModel()
                self.partialPathVnf[(pIndex, vnfI)] = pM.getExpectedServerResource(vnfI, lp)[0]
        self.logger.debug("requestVnf:{0}".format(self.partialPathVnf))

    def _genRequestLoad(self):
        self.requestLoad = {}   # [pIndex, vnfI, vnfJ, u, v]
        for pIndex, vnfI, vnfJ in self.virtualLink:
            lp = self.requestPartialPathTrafficDemand[pIndex]
            for u,v in self.phsicalLink:
                self.requestLoad[(pIndex, vnfI, vnfJ, u, v)] = lp

    def _trans2LPAndSolve(self):
        try:
            # Clear environment
            disposeDefaultEnv()

            # Create optimization model
            m = gp.Model('PartialLP')

            # timeout setting
            m.setParam('TimeLimit', 1000)

            # Create continuous variables
            # help(Model.addVars)
            flow = m.addVars(self.virtualLink, self.phsicalLink, vtype=GRB.CONTINUOUS, name="flow", lb=0.0, ub=1.0)
            k = m.addVar(vtype=GRB.CONTINUOUS, name="k")
            a = m.addVars(self.partialPathVnf, self.switches, vtype=GRB.CONTINUOUS, name="deploy", lb=0.0, ub=1.0)

            # # Create binary variables
            # flow = m.addVars(self.virtualLink, self.phsicalLink, vtype=GRB.BINARY, name="flow", lb=0.0, ub=1.0)
            # k = m.addVar(vtype=GRB.CONTINUOUS, name="k")    # k is CONTINUOUS
            # a = m.addVars(self.partialPathVnf, self.switches, vtype=GRB.BINARY, name="deploy", lb=0.0, ub=1.0)

            # Flow-conservation constraints
            m.addConstrs(
                (flow.sum(pIndex, 0, '*', '*', self.requestPartialPathSrcSwitchID[pIndex]) - flow.sum(pIndex, 0, '*', self.requestPartialPathSrcSwitchID[pIndex], '*') == -1 * (1 - a.sum(pIndex, vnfJ, self.requestPartialPathSrcSwitchID[pIndex]))
                    for pIndex, vnfI, vnfJ in self.virtualLink if vnfI == 0
                    ), "srcNode")

            m.addConstrs(
                (flow.sum(pIndex, '*', -1, '*', self.requestPartialPathDstSwitchID[pIndex]) - flow.sum(pIndex, '*', -1, self.requestPartialPathDstSwitchID[pIndex], '*') == 1 * (1 - a.sum(pIndex, vnfI, self.requestPartialPathDstSwitchID[pIndex]))
                    for pIndex, vnfI, vnfJ in self.virtualLink if vnfJ == -1
                    ), "dstNode")

            m.addConstrs(
                (flow.sum(pIndex, vnfI, vnfJ, '*', w) - flow.sum(pIndex, vnfI, vnfJ, w, '*') == a.sum(pIndex, vnfJ, w) - a.sum(pIndex, vnfI, w)
                    for pIndex, vnfI, vnfJ in self.virtualLink
                    for w in self.switches
                    ), "middleNode")

            # VNF deployment constraints
            m.addConstrs(
                (a.sum(pIndex, vnfI, '*') == 1 for pIndex, vnfI in self.partialPathVnf.keys()), "vnfDeployNode")

            # some switch only forward, can't provide vnf
            m.addConstrs(
                (a.sum(pIndex, vnfI, [w for w in self.switches if (vnfI in self._dib.getSwitch(w, self.zoneName).supportVNF and w != self.requestPartialPathBp[pIndex]) ]   ) == 1
                    for pIndex, vnfI in self.partialPathVnf.keys() if vnfI not in [0, -1]
                    ),
                    "vnfDeployNode")

            # fix the vnf 0 and vnf -1
            m.addConstrs(
                (a.sum(pIndex, 0, w) == 1
                for pIndex, w in self.requestPartialPathSrcSwitchID.items()), "vnfDeployNode")
            m.addConstrs(
                (a.sum(pIndex, -1, w) == 1
                for pIndex, w in self.requestPartialPathDstSwitchID.items()), "vnfDeployNode")

            # Node disjoint
            m.addConstrs(
                (flow.sum(pIndex, '*', '*', '*', self.requestPartialPathBp[pIndex]) + flow.sum(pIndex, '*', '*', self.requestPartialPathBp[pIndex], '*') == 0
                    for pIndex in self.requestPartialPath
                    ), "disjointNode")

            # Node capacity
            # we assume c_i == 1
            m.addConstrs(
                (a.sum('*', '*', w) - a.sum('*', [0, -1], w) <= self.switchCapacity[w]
                for w in self.switches), "nodeCapacity")

            # Link capacity
            m.addConstrs(
                (flow.prod(self.requestLoad, '*', '*', '*', u, v) <= self.linkCapacity[u,v]
                    for u,v in self.phsicalLink), "linkCapacity")

            # Node load K
            # assume all r_i == 1
            m.addConstrs(
                (a.sum('*', '*', w) - a.sum('*', [0, -1], w) <= k * self.switchCapacity[w]
                    for w in self.switches), "NPoPLoad")

            m.update()
            mkdirs("./LP/")
            # m.write("./LP/partialLP.mps")
            # m.write("./LP/partialLP.prm")
            m.write("./LP/partialLP.lp")

            # Add obj
            obj = k
            m.setObjective(obj, GRB.MINIMIZE)
            m.optimize()

            # Print solution
            if m.status == GRB.OPTIMAL:
                self.logger.info('Optimal Obj k = {0}'.format(m.objVal))

                self.jointLinkSolution = m.getAttr('x', flow)
                for items in self.virtualLink:
                    pIndex = items[0]
                    vnfI = items[1]
                    vnfJ = items[2]
                    self.logger.info('Optimal flows for pIndex {0}, vnf {1} -> vnf {2}'.format(pIndex, vnfI, vnfJ))
                    for u,v in self.phsicalLink:
                        if self.jointLinkSolution[pIndex, vnfI, vnfJ, u, v] > 0:
                            self.logger.info('%s -> %s: %g' % (u, v, self.jointLinkSolution[pIndex, vnfI, vnfJ, u, v]))

                self.vnfDeploymentSolution = m.getAttr('x', a)
                for items in self.partialPathVnf.keys():
                    pIndex = items[0]
                    vnf = items[1]
                    for switchID in self.switches:
                        if self.vnfDeploymentSolution[pIndex, vnf, switchID] > 0:
                            self.logger.info(
                                "Optimal deployment for pIndex {0}, vnf {1} > switch {2}. deployment: {3}".format(
                                    pIndex, vnf, switchID, self.vnfDeploymentSolution[pIndex, vnf, switchID]))

            elif m.status == GRB.SUBOPTIMAL:
                self.logger.warning("model status: suboptimal")
            elif m.status == GRB.INFEASIBLE:
                self.logger.warning("infeasible model")
                raise ValueError("infeasible model")
            else:
                self.logger.warning("unknown model status:{0}".format(m.status))

        except GurobiError:
            self.logger.error('Error reported')

        finally:
            del m
            # clean up gruobi environment
            disposeDefaultEnv()
