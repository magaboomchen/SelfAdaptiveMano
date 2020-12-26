#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
original sfc mapping
[2018][globecom]Partial Rerouting for High-Availability and
Low-Cost Service Function Chain
'''

import copy

import gurobipy as gp
from gurobipy import GRB
from gurobipy import *

from sam.base.path import *
from sam.base.server import *
from sam.base.messageAgent import *
from sam.base.socketConverter import *
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.orchestration.algorithms.multiLayerGraph import *


class OPSFC(object):
    def __init__(self, dib, requestBatchList):
        self._dib = dib
        self.requestBatchList = requestBatchList
        self._sc = SocketConverter()

        logConfigur = LoggerConfigurator(__name__, './log',
            'OPSFC.log', level='debug')
        self.logger = logConfigur.getLogger()

    def init(self):
        self.requestList = copy.deepcopy(self.requestBatchList)
        # self.logger.debug(self.requestBatchList)
        # raw_input()
        self.switches = {}
        self.requestVnf = {}
        self.phsicalLink = gp.tuplelist()
        self.virtualLink = {}
        self.mapResults = {}

    def mapSFCI(self):
        self.logger.info("mapSFCI")
        self.init()
        self.opSFC()

        return self.mapResults

    def opSFC(self):
        self._genVariablesAndConsts()
        self._trans2LP()
        self._randomizedRoundingAlgorithm()

    def _genVariablesAndConsts(self):
        # f^{r}_{0,mr,u,sr}
        self._genPhysicalLinksVar() # C_{u,v}
        self._genVirtualLinkVar()
        # A^r_{i,w}
        self._genSwitchesVar()  # C_w
        self._genVnfVar()
        # l_r
        self._genRequestLoad()
        # s_r, t_r
        self._genRequestIngAndEg()

    def _genPhysicalLinksVar(self):
        self.links = {}
        for key, link in self._dib.getLinksByZone(SIMULATOR_ZONE).items():
            (srcNodeID,dstNodeID) = key
            self.links[(srcNodeID,dstNodeID)] = link.bandwidth

        self.phsicalLink , self.linkCapacity = gp.multidict(self.links)

        self.logger.info("phsicalLink:{0}, self.linkCapacity:{1}".format(
            self.phsicalLink, self.linkCapacity))

    def _genSwitchesVar(self):
        self.switches = {}
        for switchID, switch in self._dib.getSwitchesByZone(SIMULATOR_ZONE).items():
            self.switches[switchID] = [self._getServerClusterCapacity(switch)]
        self.switches, self.switchCapacity = gp.multidict(self.switches)
        self.logger.info("switches:{0}".format(self.switches))

    def _getServerClusterCapacity(self, switch):
        # for the sake of simplicity, we only use cpu core as capacity
        coreNum = 0
        for serverID, server in self._dib.getServersByZone(SIMULATOR_ZONE).items():
            if self._isServerUnderSwitch(switch, serverID) and \
                server.getServerType() != SERVER_TYPE_CLASSIFIER:
                coreNum = coreNum + server.getMaxCores()
        return coreNum

    def _isServerUnderSwitch(self, switch, serverID):
        # self.logger.debug(self.switches)
        switchLanNet = switch.lanNet
        server = self._dib.getServer(serverID, SIMULATOR_ZONE)
        serverIP = server.getDatapathNICIP()
        if self._sc.isLANIP(serverIP, switchLanNet):
            return True
        else:
            return False

    def _genVnfVar(self):
        self.requestVnf = {}
        for rIndex in range(len(self.requestList)):
            request = self.requestList[rIndex]
            sfc = request.attributes['sfc']
            for vnf in sfc.vNFTypeSequence:
                self.requestVnf[(rIndex, vnf)] = 1  # load per vnf
            self.requestVnf[(rIndex, 0)] = 1
            self.requestVnf[(rIndex, -1)] = 1
        self.logger.debug("self.requestVnf:{0}".format(self.requestVnf))

    def _genVirtualLinkVar(self):
        self.virtualLink = {}
        for rIndex in range(len(self.requestList)):
            request = self.requestList[rIndex]
            sfc = request.attributes['sfc']
            self.logger.debug("sfc.vNFTypeSequence:{0}".format(sfc.vNFTypeSequence))
            m_r = sfc.vNFTypeSequence[0]
            n_r = sfc.vNFTypeSequence[-1]
            self.virtualLink[(rIndex, 0, m_r)] = 1
            self.virtualLink[(rIndex, n_r, -1)] = 1
            for index in range(len(sfc.vNFTypeSequence)-1):
                vnfI = sfc.vNFTypeSequence[index]
                vnfJ = sfc.vNFTypeSequence[index+1]
                self.virtualLink[(rIndex, vnfI, vnfJ)] = 1
        self.virtualLink, virtualLinkState = gp.multidict(self.virtualLink)
        self.logger.debug("self.virtualLink:{0}".format(self.virtualLink))

    def _genRequestLoad(self):
        self.requestLoad = {}
        for rIndex in range(len(self.requestList)):
            request = self.requestList[rIndex]
            sfc = request.attributes['sfc']
            load = sfc.slo.throughput
            for items in self.virtualLink:
                if items[0] == rIndex:
                    vnfI = items[1]
                    vnfJ = items[2]
                    for u,v in self.phsicalLink:
                        self.requestLoad[(rIndex, vnfI, vnfJ, u, v)] = load
                        # self.logger.debug("type:{0}".format(type(load)))
                        # self.logger.debug("rIndex:{0}, load:{1}".format(rIndex, load))

    def _genRequestIngAndEg(self):
        self.requestIng = {}
        self.requestEg = {}
        for rIndex in range(len(self.requestList)):
            request = self.requestList[rIndex]
            sfc = request.attributes['sfc']
            ingress = sfc.directions[0]['ingress']
            egress = sfc.directions[0]['egress']
            # self.logger.debug("ingress:{0}".format(ingress))
            # raw_input()
            ingSwitch = self._dib.getConnectedSwitch(ingress.getServerID(),
                SIMULATOR_ZONE)
            ingSwitchID = ingSwitch.switchID
            egSwitch = self._dib.getConnectedSwitch(egress.getServerID(),
                SIMULATOR_ZONE)
            egSwitchID = egSwitch.switchID
            self.logger.debug("ingSwitchID:{0}, egSwitchID:{1}".format(
                ingSwitchID,egSwitchID))
            self.requestIng[rIndex] = ingSwitchID
            self.requestEg[rIndex] = egSwitchID
        self.logger.debug("self.requestIng:{0}".format(self.requestIng))

    def _trans2LP(self):
        try:
            # Clear environment
            disposeDefaultEnv()

            # Create optimization model
            m = gp.Model('opSFC')

            # Create continuous variables
            # help(Model.addVars)
            flow = m.addVars(self.virtualLink, self.phsicalLink, vtype=GRB.CONTINUOUS, name="flow")
            k = m.addVar(vtype=GRB.CONTINUOUS, name="k")
            a = m.addVars(self.requestVnf, self.switches, vtype=GRB.CONTINUOUS, name="deploy")

            # Create binary variables
            # flow = m.addVars(self.virtualLink, self.phsicalLink, vtype=GRB.BINARY, name="flow")
            # k = m.addVar(vtype=GRB.CONTINUOUS, name="k")    # k is CONTINUOUS
            # a = m.addVars(self.requestVnf, self.switches, vtype=GRB.BINARY, name="deploy")

            # Flow-conservation constraints
            m.addConstrs(
                (flow.sum(rIndex, 0, '*', '*', self.requestIng[rIndex]) - flow.sum(rIndex, 0, '*', self.requestIng[rIndex], '*') == -1 * (1 - a.sum(rIndex, vnfJ, self.requestIng[rIndex]))
                    # for rIndex in range(len(self.requestList))
                    for rIndex, vnfI, vnfJ in self.virtualLink if vnfI == 0
                    ), "srcNode")

            m.addConstrs(
                (flow.sum(rIndex, '*', -1, '*', self.requestEg[rIndex]) - flow.sum(rIndex, '*', -1, self.requestEg[rIndex], '*') == 1 * (1 - a.sum(rIndex, vnfI, self.requestEg[rIndex]))
                    # for rIndex in range(len(self.requestList))
                    for rIndex, vnfI, vnfJ in self.virtualLink if vnfJ == -1
                    ), "dstNode")

            m.addConstrs(
                (flow.sum(rIndex, vnfI, vnfJ, '*', w) - flow.sum(rIndex, vnfI, vnfJ, w, '*') == a.sum(rIndex, vnfJ, w) - a.sum(rIndex, vnfI, w)
                    for rIndex, vnfI, vnfJ in self.virtualLink
                    # for w in self.switches if w != self.requestIng[rIndex] and w != self.requestEg[rIndex]
                    for w in self.switches
                    ), "middleNode")

            # VNF deployment constraints
            m.addConstrs(
                (a.sum(rIndex, vnfI, '*') == 1 for rIndex, vnfI in self.requestVnf.keys()), "vnfDeployNode")

            # some switch only forward, can't provide vnf
            m.addConstrs(
                (a.sum(rIndex, vnfI, [w for w in self.switches if vnfI in self._dib.getSwitch(w, SIMULATOR_ZONE).supportVNF ]) == 1 
                    for rIndex, vnfI in self.requestVnf.keys() if vnfI not in [0, -1]
                    ),
                    "vnfDeployNode")

            # fix the vnf 0 and vnf -1
            m.addConstrs(
                (a.sum(rIndex, 0, w) == 1
                for rIndex, w in self.requestIng.items()), "vnfDeployNode")
            m.addConstrs(
                (a.sum(rIndex, -1, w) == 1
                for rIndex, w in self.requestEg.items()), "vnfDeployNode")

            # Node capacity
            # we assume c_i == 1
            m.addConstrs(
                (a.sum('*', '*', w) - a.sum('*', [0, -1], w) <= self.switchCapacity[w] for w in self.switches), "nodeCapacity")

            # Link capacity
            m.addConstrs(
                (flow.prod(self.requestLoad, '*', '*', '*', u, v) <= self.linkCapacity[u,v]
                    for u,v in self.phsicalLink), "linkCapacity")

            # Node load K
            m.addConstrs(
                (a.sum('*', '*', w) - a.sum('*', [0, -1], w) <= k * self.switchCapacity[w]
                    for w in self.switches), "NPoPLoad")

            m.update()
            m.write("./opSFC.mps")
            m.write("./opSFC.prm")
            m.write("./opSFC.lp")

            # Add obj
            obj = k
            m.setObjective(obj, GRB.MINIMIZE)
            m.optimize()

            # Print solution
            if m.status == GRB.OPTIMAL:
                self.logger.info('Optimal Obj k = {0}'.format(m.objVal))

                self.jointLinkSolution = m.getAttr('x', flow)
                for items in self.virtualLink:
                    request = items[0]
                    vnfI = items[1]
                    vnfJ = items[2]
                    self.logger.info('Optimal flows for request {0}, vnf {1} -> vnf {2}'.format(request, vnfI, vnfJ))
                    for u,v in self.phsicalLink:
                        if self.jointLinkSolution[request, vnfI, vnfJ, u, v] > 0:
                            self.logger.info('%s -> %s: %g' % (u, v, self.jointLinkSolution[request, vnfI, vnfJ, u, v]))

                self.vnfDeploymentSolution = m.getAttr('x', a)
                for items in self.requestVnf.keys():
                    request = items[0]
                    vnf = items[1]
                    for switchID in self.switches:
                        if self.vnfDeploymentSolution[request, vnf, switchID] > 0:
                            self.logger.info(
                                "Optimal deployment for request {0}, vnf {1} > switch {2}. deployment: {3}".format(
                                    request, vnf, switchID, self.vnfDeploymentSolution[request, vnf, switchID]))
            elif m.status == GRB.SUBOPTIMAL:
                self.logger.warning("model status: suboptimal")
            elif m.status == GRB.INFEASIBLE:
                self.logger.warning("infeasible model")
            else:
                self.logger.warning("unknown model status:{0}".format(m.status))

        except GurobiError:
            self.logger.error('Error reported')

        finally:
            # clean up gruobi environment
            disposeDefaultEnv()

    def _randomizedRoundingAlgorithm(self):
        self._initRRAlgorithmsValues()
        for rIndex in range(len(self.requestList)):
            self._initCandidatePathSet()
            while self._existJointLinkLeq0():
                jointLink = self._selectJointLink()
                # self.logger.debug("jointLink:{0}".format(jointLink))
                path = self._findCandidatePath(jointLink)
                self._addCandidatePath(jointLink, path)
                self._updateJointLinkValue(jointLink, path)
            # TODO
            path = self._selectPath4Candidates()
            path = self._selectNPoPNodeAndServers(path)
            self._addPath2Sfci(path)

    def _initRRAlgorithmsValues(self):
        self.jointLink = copy.deepcopy(self.jointLinkSolution)

    def _initCandidatePathSet(self):
        self._candidatePathSet = {} # "(rIndex, i, j, u, v)": pathSet

    def _existJointLinkLeq0(self):
        # self.logger.debug("number of jointLink:{0}".format(len(self.jointLink)))
        for jointLink, value in self.jointLink.items():
            # self.logger.debug("jointLink:{0}, value:{1}".format(jointLink, value))
            if value > 0:
                return True

    def _selectJointLink(self):
        jointLinkList = [(jointLink, value) for jointLink, value in self.jointLink.items() if value > 0]
        return min(jointLinkList)

    def _findCandidatePath(self, jointLink):
        (rIndex, i, j, u, v) = jointLink[0]
        mlg = MultiLayerGraph()
        mlg.loadInstance4dibAndRequest(self._dib, self.requestList[rIndex], WEIGHT_TYPE_DELAY_MODEL)
        mlg.trans2MLG()
        self.logger.debug("_findCandidatePath")
        # 目前构建的多层图居然是空的！
        # 出现问题了，多层图构建，需要删除部分资源不足的有向边。
        raw_input()
        pathFirstHalf = mlg.getPath(0, ing, i, u)
        pathMiddleLink = mlg.getPath(i, u, i, v)
        c = self._getRequestSFCLength(self.requestList[rIndex])
        pathLatterHalf = mlg.getPath(i, v, c, eg)
        path = mlg.catPath(pathFirstHalf, pathMiddleLink)
        path = mlg.catPath(path, pathLatterHalf)
        return path

    def _getRequestSFCLength(self, request):
        sfc = request.attributes['sfc']
        return len(sfc.vNFTypeSequence)

    def _addCandidatePath(self, jointLink, path):
        self._candidatePathSet[jointLink[0]] = path

    def _updateJointLinkValue(self, jointLink):
        minusValue = self.jointLink[jointLink[0]]
        for jointLink, value in self.jointLink.items():
            if value > 0:
                self.jointLink[jointLink] = value - minusValue

    def _selectPath4Candidates(self):
        pass

    def _selectNPoPNodeAndServers(self, path):
        pass
    
    def _addPath2Sfci(self, path):
        pass
