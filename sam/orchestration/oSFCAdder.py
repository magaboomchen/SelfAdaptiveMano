#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
To add more mapping algorithms, you need add code in following functions:
* genABatchOfRequestAndAddSFCICmds()
* YOUR_MAPPING_ALGORITHM_API_CALLER()
* YOUR_MAPPING_ALGOTIYHM()
'''

from logging import Logger
import sys

if sys.version > '3':
    import queue as Queue
else:
    import Queue
import uuid
import copy
from typing import Dict, List, Tuple, Union

from sam.base.sfc import SFC, SFCI
from sam.base.slo import SLO
from sam.base.vnf import VNFI
from sam.base.switch import Switch
from sam.base.server import Server
from sam.base.messageAgent import SIMULATOR_ZONE, TURBONET_ZONE
from sam.base.sfcConstant import SFC_DIRECTION_0, SFC_DIRECTION_1
from sam.base.path import DIRECTION0_PATHID_OFFSET, MAPPING_TYPE_MMLPSFC, \
                            ForwardingPathSet, \
                            MAPPING_TYPE_E2EP, MAPPING_TYPE_UFRR, \
                            MAPPING_TYPE_NOTVIA_PSFC, MAPPING_TYPE_NETPACK, \
                            MAPPING_TYPE_INTERFERENCE, MAPPING_TYPE_NONE, \
                            MAPPING_TYPE_NETSOLVER_ILP
from sam.base.command import Command, CMD_TYPE_ADD_SFC, CMD_TYPE_ADD_SFCI
from sam.base.request import REQUEST_TYPE_ADD_SFCI, REQUEST_TYPE_ADD_SFC, \
                                REQUEST_TYPE_DEL_SFC, REQUEST_TYPE_DEL_SFCI, \
                                Request
from sam.base.socketConverter import SocketConverter
from sam.measurement.dcnInfoBaseMaintainer import DCNInfoBaseMaintainer
from sam.orchestration.oConfig import DEFAULT_MAPPING_TYPE
from sam.orchestration.vnfiIDAssigner import VNFIIDAssigner
from sam.orchestration.algorithms.pSFC.pSFC import PSFC
from sam.orchestration.algorithms.oPSFC.oPSFC import OPSFC
from sam.orchestration.algorithms.notVia.notVia import NotVia
from sam.orchestration.algorithms.dpSFCCG.dpSFCCG import DPSFCCG
from sam.orchestration.algorithms.mMLPSFC.mMLPSFC import MMLPSFC
from sam.orchestration.algorithms.mMLBSFC.mMLBSFC import MMLBSFC
from sam.orchestration.algorithms.netPack.netPack import NetPack
from sam.orchestration.algorithms.netSolverILP.netSolverILP import NetSolverILP
from sam.orchestration.algorithms.base.performanceModel import PerformanceModel


class OSFCAdder(object):
    def __init__(self, dib, # type: DCNInfoBaseMaintainer
                    logger, # type: Logger
                    podNum=None,    # type: Union[None, int]
                    minPodIdx=None,    # type: Union[None, int]
                    maxPodIdx=None,    # type: Union[None, int]
                    topoType="fat-tree",    # type: str
                    zoneName=None    # type: Union[SIMULATOR_ZONE, TURBONET_ZONE]
                ):
        self._dib = dib 
        self.logger = logger
        self._via = VNFIIDAssigner()
        self._sc = SocketConverter()
        self.zoneName = zoneName
        self.topoType = topoType
        self.podNum = podNum
        self.minPodIdx = minPodIdx
        self.maxPodIdx = maxPodIdx

        self.isNetPackInit = False

    def genAddSFCCmd(self, request):
        self.request = request
        self._checkAddSFCRequest()

        self.sfc = self.request.attributes['sfc']
        zoneName = self.sfc.attributes["zone"]
        assert zoneName == self.zoneName

        self._mapIngressEgress()
        self.logger.debug("sfc:{0}".format(self.sfc))

        cmd = Command(CMD_TYPE_ADD_SFC, uuid.uuid1(), attributes={
            'sfc':self.sfc, 'zone':self.zoneName
        })

        return cmd

    def _checkAddSFCRequest(self):
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
        self.logger.info("_mapIngressEgress start!")
        for direction in self.sfc.directions:
            directionID = direction['ID']
            if directionID != SFC_DIRECTION_0:
                continue
            source = direction['source']
            if source['node'] == None:
                nodeIP = source['IPv4']
                if nodeIP == "*":
                    dcnGatewaySwitch = self._selectActiveDCNGateWaySwitch()
                    source['node'] = dcnGatewaySwitch
                else:
                    source['node'] = self._dib.getServerByIP(nodeIP, self.zoneName)
                    if source['node'] == None:
                        dcnGatewaySwitch = self._selectActiveDCNGateWaySwitch()
                        source['node'] = dcnGatewaySwitch
            direction['ingress'] = self._selectClassifierByNode(source['node'])

            destination = direction['destination']
            if destination['node'] == None:
                nodeIP = destination['IPv4']
                if nodeIP == "*":
                    dcnGatewaySwitch = self._selectActiveDCNGateWaySwitch()
                    destination['node'] = dcnGatewaySwitch
                else:
                    destination['node'] = self._dib.getServerByIP(nodeIP, self.zoneName)
                    if destination['node'] == None:
                        dcnGatewaySwitch = self._selectActiveDCNGateWaySwitch()
                        destination['node'] = dcnGatewaySwitch
            direction['egress'] = self._selectClassifierByNode(destination['node'])
        if len(self.sfc.directions) == 2:
            self.mirrorDirectionsInfo()
        self.logger.info("_mapIngressEgress finish!")

    def _selectActiveDCNGateWaySwitch(self):
        switch = self._dib.randomSelectDCNGateWaySwitch(self.zoneName)
        if switch == None:
            raise ValueError("No active dcn gateway at all.")
        else:
            return switch

    def _selectClassifierByNode(self, node):
        # type: (Union[Switch, Server]) -> Union[Switch, Server]
        if type(node) == Server:
            switch = self._dib.getConnectedSwitch(node.getServerID(), self.zoneName)
            if switch.programmable == True:
                return switch
            else:
                server = self._dib.getClassifierBySwitch(switch, self.zoneName)
                return server
        elif type(node) == Switch:
            if node.programmable == True:
                return node
            else:
                server = self._dib.getClassifierBySwitch(node, self.zoneName)
                return server
        else:
            raise ValueError("Unknown node type: {0}".format(type(node)))

    def mirrorDirectionsInfo(self):
        direction0 = None
        for direction in self.sfc.directions:
            directionID = direction['ID']
            if directionID != SFC_DIRECTION_0:
                continue
            direction0 = direction

        for direction in self.sfc.directions:
            directionID = direction['ID']
            if directionID != SFC_DIRECTION_1:
                continue
            direction['source'] = direction0['destination']
            direction['ingress'] = direction0['egress']
            direction['egress'] = direction0['ingress']
            direction['destination'] = direction0['source']
        self.logger.info("mirrored direcitons {0}".format(self.sfc.directions))

    # def _selectDCNGatewaySwitchInputPort(self, switch):
    #     rndIdx = random.randint(0, len(switch.gatewayPortLists)-1)
    #     return switch.gatewayPortLists[rndIdx]

    # def _selectClassifierByNode(self, nodeIdentifier):
    #     if "IPv4" in nodeIdentifier:
    #         nodeIP = nodeIdentifier["IPv4"]
    #     else:
    #         raise ValueError("Unsupport source/destination type")

    #     if nodeIP == "*":
    #         dcnGateway = self._dib.getDCNGateway()
    #         return self._dib.getClassifierBySwitch(dcnGateway, self.zoneName)
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

    def genABatchOfRequestAndAddSFCICmds(self, requestBatchQueue):
        # type: (Queue.Queue) -> List[Tuple[Request, Command]]
        self.logger.info("oSFCAdder process batch size: {0}".format(requestBatchQueue.qsize()))
        # while not requestBatchQueue.empty():
        #     request = requestBatchQueue.get()
        #     self.logger.info("request:{0}".format(request))
        #     self.logger.info("sfci:{0}".format(request.attributes["sfci"]))

        requestDict = self._divRequest(requestBatchQueue)
        # self._updateRequestDictIngAndEg(requestDict)
        # self._logRequestDict(requestDict)
        reqCmdTupleList = []
        for mappingType in requestDict.keys():
            requestBatchList = requestDict[mappingType]
            # You can add more algorithms here
            # mappingType is defined in sam/base/path.py
            if mappingType == MAPPING_TYPE_UFRR:
                self.logger.info("ufrr")
                forwardingPathSetsDict = self.ufrr(requestBatchList)
            elif mappingType == MAPPING_TYPE_MMLPSFC:
                self.logger.info("mMLPSFC")
                forwardingPathSetsDict = self.mMLPSFC(requestBatchList)
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
                forwardingPathSetsDict = {}
                for rIndex in range(len(requestBatchList)):
                    forwardingPathSetsDict[rIndex] = ForwardingPathSet(
                        {DIRECTION0_PATHID_OFFSET:0}, mappingType,
                        {DIRECTION0_PATHID_OFFSET:{}})
            else:
                self.logger.error(
                    "Unknown mappingType {0}".format(mappingType))
                raise ValueError("Unknown mappingType.")

            self.logger.info("forwardingPathSetsDict is {0}".format(forwardingPathSetsDict))

            reqCmdTupleList.extend(
                self._forwardingPathSetsDict2Cmd(forwardingPathSetsDict,
                    requestBatchList)
            )

            # if mappingType in [MAPPING_TYPE_UFRR, MAPPING_TYPE_E2EP, MAPPING_TYPE_NOTVIA_PSFC, \
            #                     MAPPING_TYPE_NETPACK, MAPPING_TYPE_NETSOLVER_ILP, MAPPING_TYPE_NONE]:
            #     reqCmdTupleList.extend(
            #         self._forwardingPathSetsDict2Cmd(forwardingPathSetsDict,
            #             requestBatchList)
            #     )
            # # elif mappingType in [MAPPING_TYPE_NETPACK, MAPPING_TYPE_NETSOLVER_ILP, MAPPING_TYPE_NONE]:
            # #     reqCmdTupleList.extend(
            # #         self._netPackForwardingPathSetsDict2Cmd(forwardingPathSetsDict,
            # #             requestBatchList)
            # #     )
            # else:
            #     raise ValueError("Unimplement mapping type: {0}".format(mappingType))

        return reqCmdTupleList

    def _divRequest(self, requestBatchQueue):
        # type: (Queue.Queue) -> Dict[str, List[Request]]
        requestDict = {}    # type: Dict[str, List[Request]]
        while not requestBatchQueue.empty():
            request = copy.deepcopy(requestBatchQueue.get())
            # self.logger.debug(request)
            # self.logger.debug("*****************")
            if 'mappingType' in request.attributes:
                mappingType = request.attributes['mappingType']
            else:
                mappingType = DEFAULT_MAPPING_TYPE
                request.attributes['mappingType'] = mappingType
            if mappingType not in requestDict.keys():
                requestDict[mappingType] = []
            requestDict[mappingType].append(request)
            # self.logger.debug(requestDict[mappingType])
        return requestDict

    def _updateRequestDictIngAndEg(self, requestDict):
        for mappingType,requestList in requestDict.items():
            for request in requestList:
                self.request = request
                self._checkAddSFCIRequest()

                self.sfc = self.request.attributes['sfc']
                self.zoneName = self.sfc.attributes["zone"]

                # self._mapIngressEgress()
                # self.logger.debug("sfc:{0}".format(self.sfc))

    def _checkAddSFCIRequest(self):
        if self.request.requestType  == REQUEST_TYPE_ADD_SFCI or\
                self.request.requestType  == REQUEST_TYPE_DEL_SFCI:
            if 'sfc' not in self.request.attributes:
                raise ValueError("Request missing sfc")
            if 'sfci' not in self.request.attributes:
                raise ValueError("Request missing sfci")
            sfc = self.request.attributes['sfc']
            if sfc.directions[0]["ingress"] == None \
                    or sfc.directions[0]["egress"] == None:
                raise ValueError("Request missing sfc's ingress and egress!")
        elif self.request.requestType  == REQUEST_TYPE_ADD_SFC or\
                self.request.requestType  == REQUEST_TYPE_DEL_SFC:
            if 'sfc' not in self.request.attributes:
                raise ValueError("Request missing sfc")
        else:
            raise ValueError("Unknown request type.")

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

    def mMLPSFC(self, requestBatchList):
        mMLPSFC = MMLPSFC(self._dib, requestBatchList)
        forwardingPathSetsDict = mMLPSFC.mapSFCI()
        for key,fpsd in forwardingPathSetsDict.items():
            if fpsd != None:
                fpsd.mappingType = MAPPING_TYPE_MMLPSFC
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
        netSolverILP = NetSolverILP(self._dib, requestBatchList, self.topoType)
        forwardingPathSetsDict = netSolverILP.mapSFCI(self.podNum, 
                                        self.minPodIdx, self.maxPodIdx)

        return forwardingPathSetsDict

    def initNetPack(self):
        self.nPInstance = NetPack(self._dib, self.topoType, argsDict={
                                        "podNum": self.podNum,
                                        "minPodIdx": self.minPodIdx,
                                        "maxPodIdx": self.maxPodIdx,
                                        "zone": self.zoneName
                                    })
        self.isNetPackInit = True

    def netPack(self, requestBatchList):
        # self.logger.debug(" OSFCAdder self._dib: {0}".format(self._dib))
        if not self.isNetPackInit:
            self.initNetPack()
        netPackResultDict = self.nPInstance.mapSFCI(requestBatchList)
        return netPackResultDict["forwardingPathSetsDict"]

    def _forwardingPathSetsDict2Cmd(self, forwardingPathSetsDict,
                                        requestBatchList):
        self.logger.debug("requestFPSet:{0}".format(forwardingPathSetsDict))
        reqCmdTupleList = []
        for rIndex in range(len(requestBatchList)):
            request = requestBatchList[rIndex]
            sfc = request.attributes['sfc']
            zoneName = sfc.attributes['zone']   # type: SFC
            sfci = request.attributes['sfci']   # type: SFCI
            if forwardingPathSetsDict[rIndex] != None:
                sfci.forwardingPathSet = forwardingPathSetsDict[rIndex]
                sfci.sloRealTimeValue = SLO()
                self.logger.info("before trans, forwardingPathSet is {0}".format(sfci.forwardingPathSet))
                self.logger.warning("before sfci.vnfiSequence: {0}".format(sfci.vnfiSequence))
                # if sfci.vnfiSequence in [None,[]]:
                #     sfci.vnfiSequence = self._getVNFISeqFromForwardingPathSet(sfc,
                #                                             sfci.forwardingPathSet)
                sfci.vnfiSequence = self._getVNFISeqFromForwardingPathSet(sfc,
                                                        sfci.forwardingPathSet)
                self.logger.warning("after sfci.vnfiSequence: {0}".format(sfci.vnfiSequence))
                cmd = Command(CMD_TYPE_ADD_SFCI, uuid.uuid1(), attributes={
                    'sfc':sfc, 'sfci':sfci, 'zone':zoneName
                })
            else:
                cmd = None
            reqCmdTupleList.append((request, cmd))
        return reqCmdTupleList

    # def _netPackForwardingPathSetsDict2Cmd(self, forwardingPathSetsDict,
    #                                     requestBatchList):
    #     self.logger.warning("This function may be deprecated in the futures, we will transform netPack to compatible with our forwarding path format")
    #     # self.logger.debug("requestFPSet:{0}".format(forwardingPathSetsDict))
    #     reqCmdTupleList = []
    #     for rIndex in range(len(requestBatchList)):
    #         request = requestBatchList[rIndex]
    #         sfc = request.attributes['sfc']
    #         zoneName = sfc.attributes['zone']
    #         sfci = request.attributes['sfci']
    #         sfci.forwardingPathSet = forwardingPathSetsDict[rIndex]
    #         # TODO: Can't use following codes, we need to transform netPack to compatible with our forwarding path format first!
    #         if sfci.vnfiSequence in [None,[]]:
    #             sfci.vnfiSequence = self._getVNFISeqFromForwardingPathSet(sfc,
    #                                                     sfci.forwardingPathSet)
    #         cmd = Command(CMD_TYPE_ADD_SFCI, uuid.uuid1(), attributes={
    #             'sfc':sfc, 'sfci':sfci, 'zone':zoneName
    #         })
    #         reqCmdTupleList.append((request, cmd))
    #     return reqCmdTupleList

    def _getVNFISeqFromForwardingPathSet(self, sfc, forwardingPathSet):
        sfcLength = len(sfc.vNFTypeSequence)
        self.logger.info("sfcLength is {0}".format(sfcLength))
        tD = sfc.getSFCTrafficDemand()
        pM = PerformanceModel()
        vSeq = []
        for stage in range(sfcLength):
            vnfType = sfc.vNFTypeSequence[stage]
            config = sfc.vnfSequence[stage].config
            vnfiList = []
            nodeList = self._getNodeListOfStage4FPSet(forwardingPathSet, stage)
            for node in nodeList:
                if type(node) == Server:
                    vnfiID = self._via._assignVNFIID(vnfType, node.getServerID())
                elif type(node) == Switch:
                    vnfiID = self._via._assignVNFIID(vnfType, node.switchID)
                else:
                    raise ValueError("Unknown node type {0}".format(type(node)))
                vnfi = VNFI(vnfType, vnfType, vnfiID, config, node)
                vnfi.maxCPUNum = pM.getExpectedServerResource(vnfType, tD)[0]
                vnfiList.append(vnfi)
            vSeq.append(vnfiList)
        return vSeq

    def _getNodeListOfStage4FPSet(self, forwardingPathSet, stage):
        nodeIDDict = {}
        # get node from primary fp
        primaryForwardingPath = forwardingPathSet.primaryForwardingPath[1]
        (vnfLayerNum, nodeID) = primaryForwardingPath[stage][-1]
        self.logger.info("vnfLayerNum is {0}, nodeID is {1}".format(vnfLayerNum, nodeID))
        # nodeID = primaryForwardingPath[stage][-1][1]
        nodeIDDict[nodeID] = nodeID

        # get mapping type
        mappingType = forwardingPathSet.mappingType

        # get node from backup fp
        backupForwardingPathDict = forwardingPathSet.backupForwardingPath[1]
        for key, backupForwardingPath in backupForwardingPathDict.items():
            if mappingType == MAPPING_TYPE_NOTVIA_PSFC:
                if self._isFRRKey(key):
                    continue
            for backupPathStageIndex in range(len(backupForwardingPath)):
                (vnfLayerNum, nodeID) = backupForwardingPath[backupPathStageIndex][-1]
                if vnfLayerNum == stage:
                    nodeIDDict[nodeID] = nodeID

        nodeList = []
        for nodeID in nodeIDDict.keys():
            self.logger.debug("nodeID:{0}".format(nodeID))
            if self._dib.isServerID(nodeID):
                node = self._dib.getServer(nodeID, self.zoneName)
            elif self._dib.isSwitchID(nodeID):
                node = self._dib.getSwitch(nodeID, self.zoneName)
            else:
                raise ValueError("Unknown node ID {0}".format(nodeID))
            nodeList.append(node)

        return nodeList

    # def _getServerListOfStage4FPSet(self, forwardingPathSet, stage):
    #     serverIDDict = {}
    #     # get server from primary fp
    #     primaryForwardingPath = forwardingPathSet.primaryForwardingPath[1]
    #     (vnfLayerNum, serverID) = primaryForwardingPath[stage][-1]
    #     serverIDDict[serverID] = serverID

    #     # get mapping type
    #     mappingType = forwardingPathSet.mappingType

    #     # get server from backup fp
    #     backupForwardingPathDict = forwardingPathSet.backupForwardingPath[1]
    #     for key, backupForwardingPath in backupForwardingPathDict.items():
    #         if mappingType == MAPPING_TYPE_NOTVIA_PSFC:
    #             if self._isFRRKey(key):
    #                 continue
    #         for backupPathStageIndex in range(len(backupForwardingPath)):
    #             (vnfLayerNum, serverID) = backupForwardingPath[backupPathStageIndex][-1]
    #             if vnfLayerNum == stage:
    #                 serverIDDict[serverID] = serverID

    #     serverList = []
    #     for serverID in serverIDDict.keys():
    #         self.logger.debug("serverID:{0}".format(serverID))
    #         server = self._dib.getServer(serverID, self.zoneName)
    #         serverList.append(server)

    #     return serverList

    def _isFRRKey(self, key):
        for keyTag in key:
            if keyTag == ("repairMethod", "fast-reroute"):
                return True
        else:
            return False
