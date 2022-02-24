#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
To add more mapping algorithms, you need add code in following functions:
* genABatchOfRequestAndAddSFCICmds()
* YOUR_MAPPING_ALGORITHM_API_CALLER()
* YOUR_MAPPING_ALGOTIYHM()
'''


import uuid
import copy

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
from sam.orchestration.vnfiIDAssigner import *
from sam.orchestration.algorithms.pSFC.pSFC import *
from sam.orchestration.algorithms.oPSFC.oPSFC import *
from sam.orchestration.algorithms.notVia.notVia import *
from sam.orchestration.algorithms.dpSFCCG.dpSFCCG import *
from sam.orchestration.algorithms.mMLPSFC.mMLPSFC import *
from sam.orchestration.algorithms.mMLBSFC.mMLBSFC import *
from sam.orchestration.algorithms.netPack.netPack import *
from sam.orchestration.algorithms.netSolverILP.netSolverILP import *
from sam.orchestration.algorithms.base.resourceAllocator import *
from sam.orchestration.algorithms.base.performanceModel import *


class OSFCAdder(object):
    def __init__(self, dib, logger, podNum=None, minPodIdx=None, maxPodIdx=None):
        self._dib = dib
        self.logger = logger
        self._via = VNFIIDAssigner()
        self._sc = SocketConverter()
        self.zoneName = None
        self.podNum = podNum
        self.minPodIdx = minPodIdx
        self.maxPodIdx = maxPodIdx

        self.nPInstance = NetPack(self._dib)

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

    # def genAddSFCICmd(self, request):
    #     self.request = request
    #     self._checkRequest()

    #     self.sfc = self.request.attributes['sfc']
    #     self.zoneName = self.sfc.attributes["zone"]

    #     self._mapIngressEgress()    # TODO: get sfc from database
    #     self.logger.debug("sfc:{0}".format(self.sfc))

    #     self.sfci = self.request.attributes['sfci']

    #     self._mapVNFI()
    #     self.logger.debug("sfci:{0}".format(self.sfci))

    #     self._mapForwardingPath()
    #     self.logger.debug("ForwardingPath:{0}".format(
    #         self.sfci.forwardingPathSet))

    #     cmd = Command(CMD_TYPE_ADD_SFCI, uuid.uuid1(), attributes={
    #         'sfc':self.sfc, 'sfci':self.sfci, 'zone':self.zoneName
    #     })

    #     return cmd

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

    # def _selectClassifier(self, nodeIdentifier):
    #     if "IPv4" in nodeIdentifier:
    #         nodeIP = nodeIdentifier["IPv4"]
    #     else:
    #         raise ValueError("Unsupport source/destination type")

    #     if nodeIP == "*":
    #         dcnGateway = self._getDCNGateway()
    #         return self._getClassifierBySwitch(dcnGateway)
    #     else:
    #         for serverInfoDict in self._dib.getServersByZone(self.zoneName).values():
    #             server = serverInfoDict['server']
    #             serverType = server.getServerType()
    #             if serverType != SERVER_TYPE_CLASSIFIER:
    #                 continue
    #             serverID = server.getServerID()
    #             switch = self._dib.getConnectedSwitch(serverID, self.zoneName)
    #             lanNet = switch.lanNet
    #             if self._sc.isLANIP(nodeIP, lanNet):
    #                 return server
    #         else:
    #             raise ValueError("Find ingress/egress failed")

    # def _getDCNGateway(self):
    #     dcnGateway = None
    #     switchesInfoDict = self._dib.getSwitchesByZone(self.zoneName)
    #     # self.logger.warning(switchesInfoDict)
    #     for switchInfoDict in switchesInfoDict.itervalues():
    #         switch = switchInfoDict['switch']
    #         # self.logger.debug(switch)
    #         if switch.switchType == SWITCH_TYPE_DCNGATEWAY:
    #             # self.logger.debug(
    #             #     "switch.switchType:{0}".format(switch.switchType)
    #             #     )
    #             dcnGateway = switch
    #             break
    #     else:
    #         raise ValueError("Find DCN Gateway failed")
    #     return dcnGateway

    # def _getClassifierBySwitch(self, switch):
    #     self.logger.debug(self._dib.getServersByZone(self.zoneName))
    #     for serverInfoDict in self._dib.getServersByZone(self.zoneName).values():
    #         server = serverInfoDict['server']
    #         self.logger.debug(server)
    #         ip = server.getDatapathNICIP()
    #         self.logger.debug(ip)
    #         serverType = server.getServerType()
    #         if serverType == SERVER_TYPE_CLASSIFIER:
    #             self.logger.debug(
    #                 "server type is classifier " \
    #                 "ip:{0}, switch.lanNet:{1}".format(ip, switch.lanNet))
    #         if self._sc.isLANIP(ip, switch.lanNet) and \
    #             serverType == SERVER_TYPE_CLASSIFIER:
    #             return server
    #     else:
    #         raise ValueError("Find ingress/egress failed")

    # def _mapVNFI(self):
    #     iNum = self.sfc.backupInstanceNumber
    #     length = len(self.sfc.vNFTypeSequence)
    #     vSeq = []
    #     for stage in range(length):
    #         vnfType = self.sfc.vNFTypeSequence[stage]
    #         vnfiList = self._roundRobinSelectServers(vnfType, iNum)
    #         vSeq.append(vnfiList)
    #     self.sfci.vnfiSequence = vSeq

    # def _roundRobinSelectServers(self, vnfType, iNum):
    #     vnfiList = []
    #     for serverInfoDict in self._dib.getServersByZone(self.zoneName).values():
    #         server = serverInfoDict['server']
    #         if server.getServerType() == 'nfvi':
    #             vnfi = VNFI(vnfType, vnfType, uuid.uuid1(), None, server)
    #             vnfiList.append(vnfi)
    #     return vnfiList

    # def _mapForwardingPath(self):
    #     self._pC = PathComputer(self._dib, self.request, self.sfci,
    #         self.logger)
    #     self._pC.mapPrimaryFP()
    #     if self.sfci.forwardingPathSet.mappingType != None:
    #         self._pC.mapBackupFP()

    def genABatchOfRequestAndAddSFCICmds(self, requestBatchQueue):
        self.logger.info("oSFCAdder process batch size: {0}".format(requestBatchQueue.qsize()))
        # while not requestBatchQueue.empty():
        #     request = requestBatchQueue.get()
        #     self.logger.info("request:{0}".format(request))
        #     self.logger.info("sfci:{0}".format(request.attributes["sfci"]))

        requestDict = self._divRequest(requestBatchQueue)
        self._updateRequestDictIngAndEg(requestDict)
        # self._logRequestDict(requestDict)
        reqCmdTupleList = []
        for mappingType in requestDict.keys():
            requestBatchList = requestDict[mappingType]
            # You can add more algorithms here
            # mappingType is defined in sam/base/path.py
            if mappingType == MAPPING_TYPE_UFRR:
                self.logger.info("ufrr")
                forwardingPathSetsDict = self.ufrr(requestBatchList)
            elif mappingType == MAPPING_TYPE_E2EP:
                self.logger.info("e2ep")
                forwardingPathSetsDict = self.e2eProtection(
                    requestBatchList)
            elif mappingType == MAPPING_TYPE_NOTVIA_PSFC:
                self.logger.info("PSFC NotVia")
                forwardingPathSetsDict = self.notViaPSFC(requestBatchList)
            elif mappingType == MAPPING_TYPE_INTERFERENCE:
                self.logger.info("InterferenceAware")
                forwardingPathSetsDict = self.interferenceAware(requestBatchList)
            elif mappingType == MAPPING_TYPE_NETPACK:
                self.logger.info("NetPack")
                forwardingPathSetsDict = self.netPack(requestBatchList)
            elif mappingType == MAPPING_TYPE_NETSOLVER_ILP:
                self.logger.info("NetSolver")
                forwardingPathSetsDict = self.netSolverILP(requestBatchList)
                self.logger.info("get result!")
            elif mappingType == MAPPING_TYPE_NONE:
                pass
            else:
                self.logger.error(
                    "Unknown mappingType {0}".format(mappingType))
                raise ValueError("Unknown mappingType.")

            if mappingType in [MAPPING_TYPE_UFRR, MAPPING_TYPE_E2EP, MAPPING_TYPE_NOTVIA_PSFC]:
                reqCmdTupleList.extend(
                    self._forwardingPathSetsDict2Cmd(forwardingPathSetsDict,
                        requestBatchList)
                )
            elif mappingType in [MAPPING_TYPE_NETPACK, MAPPING_TYPE_NETSOLVER_ILP]:
                reqCmdTupleList.extend(
                    self._netPackForwardingPathSetsDict2Cmd(forwardingPathSetsDict,
                        requestBatchList)
                )
            else:
                raise ValueError("Unimplement mapping type: {0}".format(mappingType))

        return reqCmdTupleList

    def _divRequest(self, requestBatchQueue):
        requestDict = {}
        while not requestBatchQueue.empty():
            request = copy.deepcopy(requestBatchQueue.get())
            # self.logger.debug(request)
            # self.logger.debug("*****************")
            # raw_input()
            if request.attributes.has_key('mappingType'):
                mappingType = request.attributes['mappingType']
            else:
                mappingType = DEFAULT_MAPPING_TYPE
                request.attributes['mappingType'] = mappingType
            if mappingType not in requestDict.keys():
                requestDict[mappingType] = []
            requestDict[mappingType].append(request)
            # self.logger.debug(requestDict[mappingType])
            # raw_input()
        return requestDict

    def _updateRequestDictIngAndEg(self, requestDict):
        for mappingType,requestList in requestDict.items():
            for request in requestList:
                self.request = request
                self._checkRequest()

                self.sfc = self.request.attributes['sfc']
                self.zoneName = self.sfc.attributes["zone"]

                # self._mapIngressEgress()
                # self.logger.debug("sfc:{0}".format(self.sfc))

    def _logRequestDict(self, requestDict):
        for mappingType,requestList in requestDict.items():
            for request in requestList:
                self.request = request
                self.sfc = self.request.attributes['sfc']
                for direction in self.sfc.directions:
                    self.logger.info(
                        "requestUUID:{0}, ingress:{1}, egress:{2}".format(
                            request.requestID,
                            direction['ingress'],
                            direction['egress']))

    def notViaPSFC(self, requestBatchList):
        opSFC = OPSFC(self._dib, requestBatchList)
        forwardingPathSetsDict = opSFC.mapSFCI()

        pSFC = PSFC(self._dib, requestBatchList,
            forwardingPathSetsDict)
        forwardingPathSetsDict = pSFC.mapSFCI()
        dibDict = pSFC.dibDict

        notVia = NotVia(self._dib, dibDict,
            requestBatchList, forwardingPathSetsDict)
        forwardingPathSetsDict = notVia.mapSFCI()

        # self.logger.debug("forwardingPathSetsDict:{0}".format(
        #         forwardingPathSetsDict))
        return forwardingPathSetsDict

    def e2eProtection(self, requestBatchList):
        dpSFC = DPSFCCG(self._dib, requestBatchList)
        forwardingPathSetsDict = dpSFC.mapSFCI()

        return forwardingPathSetsDict

    def ufrr(self, requestBatchList):
        mMLPSFC = MMLPSFC(self._dib, requestBatchList)
        forwardingPathSetsDict = mMLPSFC.mapSFCI()

        mMLBSFC = MMLBSFC(self._dib, requestBatchList,
            forwardingPathSetsDict)
        forwardingPathSetsDict = mMLBSFC.mapSFCI()

        return forwardingPathSetsDict

    def interferenceAware(self, requestBatchList):
        # you can refer to def e2eProtection(self, requestBatchList) to write your algorithm's api
        # call your algorithm's api here
        pass
        # implement your algorithm in sam/orchestration/algorithms/interferenceAware
        # (Important) vnf<->server mapping is stored in requestBatchList
        #   In details, each request in requestBatchList has a member sfci
        #   The mapping info is stored in request.sfci.vnfiSequence (please refer to sam/base/vnf.py and sam/base/sfc.py)
        # sfc path is stored in forwardingPathSetsDict
        #   If you don't need to calculate path, just leave each path in forwardingPathSetsDict to default.
        forwardingPathSetsDict = None
        return forwardingPathSetsDict

    def netSolverILP(self, requestBatchList):
        netSolverILP = NetSolverILP(self._dib, requestBatchList)
        forwardingPathSetsDict = netSolverILP.mapSFCI(self.podNum, 
                                        self.minPodIdx, self.maxPodIdx)

        return forwardingPathSetsDict

    def netPack(self, requestBatchList):
        # self.logger.debug(" OSFCAdder self._dib: {0}".format(self._dib))
        netPackResultDict = self.nPInstance.mapSFCI(requestBatchList,
                                                self.podNum, self.minPodIdx,
                                                            self.maxPodIdx)
        return netPackResultDict["forwardingPathSetsDict"]

    def _forwardingPathSetsDict2Cmd(self, forwardingPathSetsDict,
                                        requestBatchList):
        self.logger.debug("requestFPSet:{0}".format(forwardingPathSetsDict))
        reqCmdTupleList = []
        for rIndex in range(len(requestBatchList)):
            request = requestBatchList[rIndex]
            sfc = request.attributes['sfc']
            zoneName = sfc.attributes['zone']
            sfci = request.attributes['sfci']
            sfci.forwardingPathSet = forwardingPathSetsDict[rIndex]
            # self.logger.warning("before sfci.vnfiSequence: {0}".format(sfci.vnfiSequence))
            # if sfci.vnfiSequence == None:
            if sfci.vnfiSequence in [None,[]]:
                sfci.vnfiSequence = self._getVNFISeqFromForwardingPathSet(sfc,
                                                        sfci.forwardingPathSet)
            # self.logger.warning("after sfci.vnfiSequence: {0}".format(sfci.vnfiSequence))
            cmd = Command(CMD_TYPE_ADD_SFCI, uuid.uuid1(), attributes={
                'sfc':sfc, 'sfci':sfci, 'zone':zoneName
            })
            reqCmdTupleList.append((request, cmd))
        return reqCmdTupleList

    def _netPackForwardingPathSetsDict2Cmd(self, forwardingPathSetsDict,
                                        requestBatchList):
        self.logger.warning("This function may be deprecated in the futures, we will transform netPack to compatible with our forwarding path format")
        # self.logger.debug("requestFPSet:{0}".format(forwardingPathSetsDict))
        reqCmdTupleList = []
        for rIndex in range(len(requestBatchList)):
            request = requestBatchList[rIndex]
            sfc = request.attributes['sfc']
            zoneName = sfc.attributes['zone']
            sfci = request.attributes['sfci']
            sfci.forwardingPathSet = forwardingPathSetsDict[rIndex]
            # TODO: Can't use following codes, we need to transform netPack to compatible with our forwarding path format first!
            # if sfci.vnfiSequence in [None,[]]:
            #     sfci.vnfiSequence = self._getVNFISeqFromForwardingPathSet(sfc,
            #                                             sfci.forwardingPathSet)
            cmd = Command(CMD_TYPE_ADD_SFCI, uuid.uuid1(), attributes={
                'sfc':sfc, 'sfci':sfci, 'zone':zoneName
            })
            reqCmdTupleList.append((request, cmd))
        return reqCmdTupleList

    def _getVNFISeqFromForwardingPathSet(self, sfc, forwardingPathSet):
        sfcLength = len(sfc.vNFTypeSequence)
        tD = sfc.getSFCTrafficDemand()
        pM = PerformanceModel()
        vSeq = []
        for stage in range(sfcLength):
            vnfType = sfc.vNFTypeSequence[stage]
            vnfiList = []
            serverList = self._getServerListOfStage4FPSet(forwardingPathSet, stage)
            for server in serverList:
                vnfiID = self._via._assignVNFIID(vnfType, server.getServerID())
                vnfi = VNFI(vnfType, vnfType, vnfiID, None, server)
                vnfi.maxCPUNum = pM.getExpectedServerResource(vnfType, tD)[0]
                vnfiList.append(vnfi)
            vSeq.append(vnfiList)
        return vSeq

    def _getServerListOfStage4FPSet(self, forwardingPathSet, stage):
        serverIDDict = {}
        # get server from primary fp
        primaryForwardingPath = forwardingPathSet.primaryForwardingPath[1]
        (vnfLayerNum, serverID) = primaryForwardingPath[stage][-1]
        serverIDDict[serverID] = serverID

        # get mapping type
        mappingType = forwardingPathSet.mappingType

        # get server from backup fp
        backupForwardingPathDict = forwardingPathSet.backupForwardingPath[1]
        for key, backupForwardingPath in backupForwardingPathDict.items():
            if mappingType == MAPPING_TYPE_NOTVIA_PSFC:
                if self._isFRRKey(key):
                    continue
            for backupPathStageIndex in range(len(backupForwardingPath)):
                (vnfLayerNum, serverID) = backupForwardingPath[backupPathStageIndex][-1]
                if vnfLayerNum == stage:
                    serverIDDict[serverID] = serverID

        serverList = []
        for serverID in serverIDDict.keys():
            self.logger.debug("serverID:{0}".format(serverID))
            server = self._dib.getServer(serverID, self.zoneName)
            serverList.append(server)

        return serverList

    def _isFRRKey(self, key):
        for keyTag in key:
            if keyTag == ("repairMethod", "fast-reroute"):
                return True
        else:
            return False
