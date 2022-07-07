#!/usr/bin/python
# -*- coding: UTF-8 -*-

import copy

import networkx as nx

from sam.base.server import Server
from sam.base.switch import Switch
from sam.base.socketConverter import SocketConverter

# TODO: bidirection computation


class PathComputer(object):
    def __init__(self, dib, request, sfci, logger):
        self._dib = dib
        self._sc = SocketConverter()
        self.logger = logger

        self.request = request
        self.sfc = request.attributes['sfc']
        self.zoneName = self.sfc.attributes['zone']
        self.sfci = sfci
        self.multiLayerGraph = None

    def mapPrimaryFP(self):
        self.sfcLength = len(self.sfc.vNFTypeSequence)
        self.ingress = self.sfc.directions[0]["ingress"]
        self.egress = self.sfc.directions[0]["egress"]
        self.ingressIDInMLG = self._genNodeID(self.ingress.getServerID(), 0)
        self.egressIDInMLG = self._genNodeID(
                self.egress.getServerID(), self.sfcLength)

        self._genMultiLayerGraph()
        self.logger.debug(
            "multiLayerGraph edges:{0}".format(self.multiLayerGraph.edges))
        self.logger.debug(
            "multiLayerGraph nodes:{0}".format(self.multiLayerGraph.nodes))

        path = nx.dijkstra_path(self.multiLayerGraph,
            self.ingressIDInMLG, self.egressIDInMLG)
        self.logger.debug("path:{0}".format(path))

        multiStagePath = self._transPath2MultiStagePath(path)
        self.primaryFP = multiStagePath
        self.sfci.forwardingPathSet.primaryForwardingPath[1] = self.primaryFP
        self.logger.info("PathComputer, primayFP:{0}".format(self.primaryFP))

    def _genMultiLayerGraph(self):
        gList = []
        for stage in range(self.sfcLength+1):
            g = self._genOneLayer(stage)
            gList.append(g)

        mLG = nx.compose_all(gList)
        self._connectLayers(mLG)
        self.multiLayerGraph = mLG

    def _genOneLayer(self, stage):
        G = nx.DiGraph()
        e = []

        linksInfoDict = self._dib.getLinksByZone(self.zoneName)
        for key, linkInfoDict in linksInfoDict.items():
            link = linkInfoDict['link']
            s = self._genNodeID(link.srcID, stage)
            d = self._genNodeID(link.dstID, stage)
            e.append((s,d,1))
        G.add_weighted_edges_from(e)

        if stage != 0:
            self._addEdgeSwitch2Server(G, stage-1, stage)
        else:
            self._addEdge4Switch2Ingresser(G)

        if stage != self.sfcLength:
            self._addEdgeSwitch2Server(G, stage, stage)
        else:
            self._addEdge4Switch2Egresser(G)

        self.logger.debug("Graph nodes:{0}".format(G.nodes))

        return G

    def _addEdgeSwitch2Server(self, G, vnfiStage, layerStage):
        vnfiList = self.sfci.vnfiSequence[vnfiStage]
        for vnfi in vnfiList:
            node = vnfi.node
            if isinstance(node, Server):
                server = node
                serverID = server.getServerID()
                serverIDInMLG = self._genNodeID(serverID, layerStage)

                switch = self._findSwitchByServer(server)
                switchID = switch.switchID
                switchIDInMLG = self._genNodeID(switchID, layerStage)

                G.add_edge(serverIDInMLG, switchIDInMLG, weight=1)
                G.add_edge(switchIDInMLG, serverIDInMLG, weight=1)

    def _addEdge4Switch2Ingresser(self, G):
        serverID = self.ingress.getServerID()
        serverIDInMLG = self._genNodeID(serverID, 0)

        switch = self._findSwitchByServer(self.ingress)
        switchID = switch.switchID
        switchIDInMLG = self._genNodeID(switchID, 0)

        G.add_edge(serverIDInMLG, switchIDInMLG, weight=1)
        G.add_edge(switchIDInMLG, serverIDInMLG, weight=1)

    def _addEdge4Switch2Egresser(self, G):
        serverID = self.egress.getServerID()
        serverIDInMLG = self._genNodeID(serverID, self.sfcLength)

        switch = self._findSwitchByServer(self.egress)
        switchID = switch.switchID
        switchIDInMLG = self._genNodeID(switchID, self.sfcLength)

        G.add_edge(serverIDInMLG, switchIDInMLG, weight=1)
        G.add_edge(switchIDInMLG, serverIDInMLG, weight=1)

    def _findSwitchByServer(self, server):
        serverIP = server.getDatapathNICIP()
        switchesInfoDict = self._dib.getSwitchesByZone(self.zoneName)
        for key, switchInfoDict in switchesInfoDict.items():
            switch = switchInfoDict['switch']
            lanNet = switch.lanNet
            if self._sc.isLANIP(serverIP, lanNet):
                return switch
        else:
            raise ValueError("Can't find switch of a server.")

    def _genNodeID(self, nodeID, stage):
        return str(nodeID) + "_Layer" + str(stage)

    def _connectLayers(self, mLG):
        for stage in range(self.sfcLength):
            vnfiList = self.sfci.vnfiSequence[stage]
            for vnfi in vnfiList:
                node = vnfi.node
                if isinstance(node, Server):
                    nodeID = node.getServerID()
                elif isinstance(node, Switch):
                    nodeID = node.switchID
                s = self._genNodeID(nodeID, stage)
                d = self._genNodeID(nodeID, stage+1)
                mLG.add_edge(s,d,weight=1)

    def _transPath2MultiStagePath(self, path):
        multiStagePath = [ [] for i in range(self.sfcLength + 1) ]
        self.logger.debug(
            "_transPath2MultiStagePath, multiStagePath:{0}".format(
                multiStagePath))
        for index in range(len(path)):
            nodeID = path[index].split("_")[0]
            stage = int(path[index].split("_Layer")[1])
            multiStagePath[stage].append(int(nodeID))

        for index in range(len(multiStagePath)):
            if len(multiStagePath[index]) == 1:
                nodeID = multiStagePath[index][0]
                multiStagePath[index].append(int(nodeID))
        return multiStagePath

    def mapBackupFP(self):
        backupPathSet = {}
        primaryFPLength = len(self.primaryFP)
        for stageIndex in range(primaryFPLength):
            path = self.primaryFP[stageIndex]
            pathLength = len(path)
            if pathLength == 2:
                continue
            for index in range(pathLength-1):
                currentNodeID = path[index]
                nextNodeID = path[index + 1]
                mLG = copy.deepcopy(self.multiLayerGraph)
                self._deleteNodeInMLG(mLG, nextNodeID)
                self.logger.debug(
                    "pruned node {0}, mLG.edges:{1}\n".format(
                        nextNodeID, mLG.edges)
                    )
                startNodeInMLG = self._genNodeID(currentNodeID, stageIndex)
                try:
                    backupPath = self._genMultiStagePath(mLG, startNodeInMLG)
                except:
                    continue
                self._pruneNullListInMultiStagePath(backupPath)
                if (currentNodeID, nextNodeID) not in backupPathSet:
                    backupPathSet[(currentNodeID, nextNodeID)] = backupPath

        backupForwardingPath = {}
        pathID = 2
        for key,value in backupPathSet.items():
            (currentNodeID, nextNodeID) = key
            backupForwardingPath[(int(currentNodeID), int(nextNodeID),
                pathID)] = value
            pathID = pathID + 1
        self.sfci.forwardingPathSet.backupForwardingPath[1]\
            = backupForwardingPath
        self.logger.info("PathComputer, backupFP:{0}".format(backupForwardingPath))

    def _deleteNodeInMLG(self, mLG, nextNodeID):
        for stageIndex in range(self.sfcLength + 1):
            nextNodeIDInMLG = self._genNodeID(nextNodeID, stageIndex)
            self.logger.debug("try to prune node:{0}\n".format(nextNodeIDInMLG))
            try:
                mLG.remove_node(nextNodeIDInMLG)
            except:
                self.logger.error("Unknown node in multi-layer graph")

    def _genMultiStagePath(self, mLG, startNodeInMLG):
        self.egress = self.sfc.directions[0]["egress"]
        self.egressIDInMLG = self._genNodeID(
                self.egress.getServerID(), self.sfcLength)

        path = nx.dijkstra_path(mLG,
            startNodeInMLG, self.egressIDInMLG)
        self.logger.debug("path:{0}".format(path))

        multiStagePath = self._transPath2MultiStagePath(path)
        return multiStagePath

    def _pruneNullListInMultiStagePath(self, mSPath):
        try:
            while True:
                mSPath.remove([])
        except:
            pass


