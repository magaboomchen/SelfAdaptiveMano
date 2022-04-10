#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
read gml and generate topology
or read customized topology and generate topology
'''

import os
import pickle

from sam.base.sfc import *
from sam.base.link import *
from sam.base.switch import *
from sam.base.server import *
from sam.base.socketConverter import *
from sam.base.exceptionProcessor import *
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.serverController.serverManager.serverManager import *
from sam.base.topoGen.base.common import *
from sam.base.topoGen.base.mkdirs import *
from sam.base.topoGen.base.dhcpServer import *

SERVER_NUMA_CPU_DISTRIBUTION = [range(0,25,2), range(1,25,2)]
SERVER_NUMA_MEMORY_DISTRIBUTION = [256, 256]


class Topology(object):
    def __init__(self):
        self._sc = SocketConverter()
        logConfigur = LoggerConfigurator("topology", './log',
            'topology.log', level='debug')
        self.logger = logConfigur.getLogger()

    def genTestbedSW1Topology(self, expNum, nPoPNum):
        topoType = "testbed_sw1"
        topoName = "testbed_sw1_V={0}_M={1}".format(
            nPoPNum, SFC_REQUEST_NUM)
        self.startGeneration(topoType, expNum, topoName)

    def genFatTreeTopology(self, expNum, podNum, nPoPNum):
        topoType = "fat-tree"
        topoName = "fat-tree-k={0}_V={1}_M={2}".format(
            podNum, nPoPNum, SFC_REQUEST_NUM)
        self.startGeneration(topoType, expNum, topoName, podNum)

    def genVL2Topology(self, expNum, intNum, aggNum, nPoPNum):
        topoType = "VL2"
        topoName = "VL2_int={0}_agg={1}_V={2}_M={3}".format(
            intNum, aggNum, nPoPNum, SFC_REQUEST_NUM)
        self.startGeneration(topoType, expNum, topoName)

    def genLogicalTwoTierTopology(self, expNum, aggNum, torNum, nPoPNum):
        topoType = "LogicalTwoTier"
        topoName = "LogicalTwoTier_n={0}_k={1}_V={2}_M={3}".format(
            aggNum, torNum, nPoPNum, SFC_REQUEST_NUM)
        self.startGeneration(topoType, expNum, topoName)

    def genGeantTopology(self, expNum, nPoPNum):
        topoType = "Geant2012"
        topoName = "Geant2012_V={0}_M={1}".format(
            nPoPNum, SFC_REQUEST_NUM)
        self.startGeneration(topoType, expNum, topoName)

    def genAttMplsTopology(self, expNum, nPoPNum):
        topoType = "AttMpls"
        topoName = "AttMpls_V={0}_M={1}".format(
            nPoPNum, SFC_REQUEST_NUM)
        self.startGeneration(topoType, expNum, topoName)

    def genSwitchL3Topology(self, expNum, nPoPNum):
        topoType = "SwitchL3"
        topoName = "SwitchL3_V={0}_M={1}".format(
            nPoPNum, SFC_REQUEST_NUM)
        self.startGeneration(topoType, expNum, topoName)

    def genUninett2011Topology(self, expNum, nPoPNum):
        topoType = "Uninett2011"
        topoName = "Uninett2011_V={0}_M={1}".format(
            nPoPNum, SFC_REQUEST_NUM)
        self.startGeneration(topoType, expNum, topoName)

    def genAllTopologies(self, expNum):
        for topoType,topoNameList in self.genTopoNameDict().items():
            for topoName in topoNameList:
                self.startGeneration(topoType, expNum, topoName)

    def startGeneration(self, topoType, expNum, topoName, podNum=None):
        topoFilePath = "../topogen/topology/{0}/{1}/{2}.dat".format(
            topoType, expNum, topoName)

        self.logger.info("topoFilePath:{0}".format(topoFilePath))

        self.readMyTopo(topoFilePath)
        self._updateSwitchSupportVNF()
        self._updateSwitchSupportNF()
        if topoType == "LogicalTwoTier":
            self.addClassifier4LogicalTwoTier()
            self.addNFVIs4LogicalTwoTier()
        elif topoType == "fat-tree":
            self.addNFVIs4FatTree(podNum)
        elif topoType == "testbed_sw1":
            self.addNFVIs4Testbed_sw1(serverNum=1)
        else:
            self.addClassifier()
            self.addNFVIs()

        topologyDir = "./topology/{0}/{1}/".format(topoType,
            expNum)
        mkdirs(topologyDir)

        pickleFilePath \
            = "./topology/{0}/{1}/{2}.M={3}.pickle".format(
                    topoType, expNum, topoName,
                    SFC_REQUEST_NUM)

        self.logger.info("pickleFilePath:{0}".format(pickleFilePath))

        self.saveTopologyPickle(pickleFilePath)

    def readMyTopo(self, filePath):
        self.init()
        with open(filePath, 'r') as f:
            lines = f.readlines()
            self._readNodeLinkNum(lines[0])
            self._readVnfLocation(lines[1:1+VNF_NUM])
            self._readSFCSourceDst(lines[VNF_NUM+1:VNF_NUM+1+SFC_REQUEST_NUM])
            self._readLink(lines[VNF_NUM+SFC_REQUEST_NUM+1:])
            if self.linkNum == 0:
                self._readNode(lines[1:1+VNF_NUM])

    def init(self):
        self._dhcp = DHCPServer()
        self.nodeNum = 0
        self.linkNum = 0
        self.vnfLocation = {}
        self.sfcRequestSourceDst = {}
        self.links = {}
        self.switches = {}
        self.servers = {}
        self.addSFCIRequest = {}

    def _readNodeLinkNum(self, line):
        # self.logger.debug("line:{0}".format(line))
        line = self._splitLine(line)
        self.nodeNum = int(line[0])
        self.linkNum = int(line[1])

    def _readVnfLocation(self, lines):
        # self.logger.debug("lines:{0}".format(lines))
        for line in lines:
            line = self._splitLine(line)
            vnfType = int(line[0])
            self.vnfLocation[vnfType] = []
            NPoPNum = int(line[1])
            for index in range(NPoPNum):
                nodeID = int(line[index+2])
                self.vnfLocation[vnfType].append(nodeID)
        self.logger.debug("vnfLocation:{0}".format(self.vnfLocation))

    def _readSFCSourceDst(self, lines):
        # self.logger.debug("lines:{0}".format(lines))
        for line in lines:
            line = self._splitLine(line)
            number = int(line[0])
            source = int(line[1])
            dst = int(line[2])
            self.sfcRequestSourceDst[number] = (source, dst)

    def _readLink(self, lines):
        # self.logger.debug("lines:{0}".format(lines))
        for line in lines:
            line = self._splitLine(line)
            srcNodeID = int(line[0])
            dstNodeID = int(line[1])
            bw = float(line[3])
            self.links[(srcNodeID,dstNodeID)] = {
                'link':Link(srcNodeID, dstNodeID, bandwidth=bw),
                'Active':True,
                'Status':None}
            if srcNodeID not in self.switches.keys():
                self.switches[srcNodeID] = {
                    'switch': Switch(srcNodeID,
                        self._getSwitchType(srcNodeID),
                        self._dhcp.genLanNet(srcNodeID),
                        self._isSwitchProgrammable(srcNodeID)),
                    'Active':True,
                    'Status':None}
            if dstNodeID not in self.switches.keys():
                self.switches[dstNodeID] = {
                    'switch': Switch(dstNodeID,
                        self._getSwitchType(dstNodeID),
                        self._dhcp.genLanNet(dstNodeID),
                        self._isSwitchProgrammable(dstNodeID)),
                    'Active':True,
                    'Status':None}

    def _readNode(self, lines):
        # self.logger.debug("lines:{0}".format(lines))
        for line in lines:
            line = self._splitLine(line)
            vnfType = int(line[0])
            NPoPNum = int(line[1])
            nodeID = int(line[2])
            if nodeID not in self.switches.keys():
                self.switches[nodeID] = {
                    'switch': Switch(nodeID,
                        self._getSwitchType(nodeID),
                        self._dhcp.genLanNet(nodeID),
                        self._isSwitchProgrammable(nodeID)),
                    'Active':True,
                    'Status':None}
        self.logger.debug("nodes:{0}".format(self.switches))

    def _updateSwitchSupportVNF(self):
        for vnfType in self.vnfLocation.keys():
            for switchID in self.vnfLocation[vnfType]:
                if vnfType not in self.switches[switchID]['switch'].supportVNF:
                    self.switches[switchID]['switch'].supportVNF.append(vnfType)

    def _updateSwitchSupportNF(self):
        for vnfType in self.vnfLocation.keys():
            for switchID in self.vnfLocation[vnfType]:
                if vnfType not in self.switches[switchID]['switch'].supportNF:
                    self.switches[switchID]['switch'].supportNF.append(vnfType)

    def _getSwitchType(self, switchID):
        if switchID == 0:
            return SWITCH_TYPE_DCNGATEWAY
        elif self._isSFF(switchID):
            return SWITCH_TYPE_NPOP
        else:
            return SWITCH_TYPE_FORWARD

    def _isSwitchProgrammable(self, switchID):
        if self._isSFF(switchID):
            return True
        else:
            return False

    def _isSFF(self, switchID):
        for vnfType in self.vnfLocation.keys():
            if switchID in self.vnfLocation[vnfType]:
                return True
        else:
            return False

    def _splitLine(self, line):
        line = line.strip("\n")
        line = line.split("\t")
        return line

    def addNFVIs(self):
        nodeVNFSupportDict = self._getNodeVNFSupportDict()
        for nodeID, vnfTypeList in nodeVNFSupportDict.items():
            self.logger.debug("nodeID:{0} vnfTypeList:{1}".format(
                                nodeID, vnfTypeList))
            for index in range(SERVER_NUM):
                self.logger.info(
                    "addServers connecting nodeID:{0}".format(nodeID))
                serverID = self._assignServerID()
                dpIP = self._dhcp.assignIP(nodeID)
                self.logger.debug("serverID:{0} dpIP:{1}".format(serverID, dpIP))
                server = Server("eno1", dpIP, SERVER_TYPE_NFVI)
                # one NIC per server
                server.setControlNICIP(dpIP)
                # two NIC per server
                # server.setControlNICIP(self._dhcp.assignIP(nodeID))
                ctIP = server.getControlNICIP()
                self.logger.debug(
                    "addServers nodeID:{0}, dpIP:{1}, ctIP:{2}".format(
                        nodeID, dpIP, ctIP))
                server.setServerID(serverID)
                for vnfType in vnfTypeList:
                    server.addVNFSupport(vnfType)
                server.updateResource()
                server.setCoreNUMADistribution(SERVER_NUMA_CPU_DISTRIBUTION)
                server.setHugepagesTotal(SERVER_NUMA_MEMORY_DISTRIBUTION)
                self.servers[serverID] = {'Active': True,
                            'timestamp': datetime.datetime(2020, 10, 27, 0,
                                                            2, 39, 408596),
                            'server': server,
                            'Status': None}

    def addNFVIs4FatTree(self, podNum):
        nodeVNFSupportDict = self._getNodeVNFSupportDict()
        for nodeID, vnfTypeList in nodeVNFSupportDict.items():
            self.logger.debug("nodeID:{0} vnfTypeList:{1}".format(
                                nodeID, vnfTypeList))
            serverNum = podNum / 2
            for index in range(serverNum):
                self.logger.info(
                    "addServers connecting nodeID:{0}".format(nodeID))
                serverID = self._assignServerID()
                dpIP = self._dhcp.assignIP(nodeID)
                self.logger.debug("serverID:{0} dpIP:{1}".format(serverID, dpIP))
                server = Server("eno1", dpIP, SERVER_TYPE_NFVI)
                # one NIC per server
                server.setControlNICIP(dpIP)
                # two NIC per server
                # server.setControlNICIP(self._dhcp.assignIP(nodeID))
                ctIP = server.getControlNICIP()
                self.logger.debug(
                    "addServers nodeID:{0}, dpIP:{1}, ctIP:{2}".format(
                        nodeID, dpIP, ctIP))
                server.setServerID(serverID)
                for vnfType in vnfTypeList:
                    server.addVNFSupport(vnfType)
                server.fastConstructResourceInfo()
                server.setCoreNUMADistribution(SERVER_NUMA_CPU_DISTRIBUTION)
                server.setHugepagesTotal(SERVER_NUMA_MEMORY_DISTRIBUTION)
                self.servers[serverID] = {'Active': True,
                            'timestamp': datetime.datetime(2020, 10, 27, 0,
                                                            2, 39, 408596),
                            'server': server,
                            'Status': None}

    def addNFVIs4Testbed_sw1(self, serverNum):
        nodeVNFSupportDict = self._getNodeVNFSupportDict()
        for nodeID, vnfTypeList in nodeVNFSupportDict.items():
            self.logger.debug("nodeID:{0} vnfTypeList:{1}".format(
                                nodeID, vnfTypeList))
            for index in range(serverNum):
                self.logger.info(
                    "addServers connecting nodeID:{0}".format(nodeID))
                serverID = self._assignServerID()
                dpIP = self._dhcp.assignIP(nodeID)
                self.logger.debug("serverID:{0} dpIP:{1}".format(serverID, dpIP))
                server = Server("eno1", dpIP, SERVER_TYPE_NFVI)
                # one NIC per server
                server.setControlNICIP(dpIP)
                # two NIC per server
                # server.setControlNICIP(self._dhcp.assignIP(nodeID))
                ctIP = server.getControlNICIP()
                self.logger.debug(
                    "addServers nodeID:{0}, dpIP:{1}, ctIP:{2}".format(
                        nodeID, dpIP, ctIP))
                server.setServerID(serverID)
                for vnfType in vnfTypeList:
                    server.addVNFSupport(vnfType)
                server.fastConstructResourceInfo()
                server.setCoreNUMADistribution(SERVER_NUMA_CPU_DISTRIBUTION)
                server.setHugepagesTotal(SERVER_NUMA_MEMORY_DISTRIBUTION)
                self.servers[serverID] = {'Active': True,
                            'timestamp': datetime.datetime(2020, 10, 27, 0,
                                                            2, 39, 408596),
                            'server': server,
                            'Status': None}

    def addNFVIs4LogicalTwoTier(self):
        # hard-code function
        nodeVNFSupportDict = self._getNodeVNFSupportDict()
        # add servers to nodeID:2
        nodeID = 2
        self._addServer2Switch(nodeID = nodeID,
                                ctIntfName="eno1",
                                ctIP = "192.168.8.17",
                                ctMAC = "b8:ca:3a:65:f7:f8",
                                dpIP = "2.2.0.66",
                                dpMAC = "b8:ca:3a:65:f7:fa",
                                serverType = SERVER_TYPE_NFVI,
                                vnfTypeList = nodeVNFSupportDict[nodeID]
                            )

        self._addServer2Switch(nodeID = nodeID,
                                ctIntfName="eno1",
                                ctIP = "192.168.8.18",
                                ctMAC = "ec:f4:bb:da:39:44",
                                dpIP = "2.2.0.68",
                                dpMAC = "ec:f4:bb:da:39:45",
                                serverType = SERVER_TYPE_NFVI,
                                vnfTypeList = nodeVNFSupportDict[nodeID]
                            )

        # add servers to nodeID:3
        nodeID = 3
        self._addServer2Switch(nodeID = nodeID,
                                ctIntfName="eno1",
                                ctIP = "192.168.0.173",
                                ctMAC = "18:66:da:85:1c:c3",
                                dpIP = "2.2.0.100",
                                dpMAC = "00:1b:21:c0:8f:98",
                                serverType = SERVER_TYPE_NFVI,
                                vnfTypeList = nodeVNFSupportDict[nodeID],
                                coreNUMADistribution=[range(0,250,2), range(1,250,2)]
                            )

        self._addServer2Switch(nodeID = nodeID,
                                ctIntfName="eth1",
                                ctIP = "192.168.0.127",
                                ctMAC = "18:66:da:85:f9:ee",
                                dpIP = "2.2.0.98",
                                dpMAC = "b8:ca:3a:65:f7:fa",
                                serverType = SERVER_TYPE_NFVI,
                                vnfTypeList = nodeVNFSupportDict[nodeID],
                                coreNUMADistribution=[range(0,250,2), range(1,250,2)]
                            )

    def _addServer2Switch(self, nodeID, ctIntfName, ctIP, ctMAC, dpIP,
                            dpMAC, serverType, vnfTypeList,
                            coreNUMADistribution=SERVER_NUMA_CPU_DISTRIBUTION):
        if dpIP == None:
            dpIP = self._dhcp.assignIP(nodeID)
        self.logger.debug("addServers nodeID:{0}, dpIP:{1},"
                            "ctIP:{2} vnfTypeList:{3}".format(
                            nodeID, dpIP, ctIP, vnfTypeList))

        server = Server(ctIntfName, dpIP, serverType)
        server.setControlNICIP(ctIP)
        server.setControlNICMAC(ctMAC)
        server.setDataPathNICMAC(dpMAC)
        serverID = self._assignServerID()
        server.setServerID(serverID)
        for vnfType in vnfTypeList:
            server.addVNFSupport(vnfType)
        server.updateResource()
        server.setCoreNUMADistribution(coreNUMADistribution)
        server.setHugepagesTotal(SERVER_NUMA_MEMORY_DISTRIBUTION)
        self.servers[serverID] = {
            'Active': True,
            'timestamp': datetime.datetime(2020, 10, 27, 0,
                                            2, 39, 408596),
            'server': server,
            'Status':None}

    def _getNodeVNFSupportDict(self):
        nodeVNFSupportDict = {}
        for vnfType, nodeIDList in self.vnfLocation.items():
            self.logger.debug("vnfType{0}, nodeIDList:{1}".format(vnfType,nodeIDList))
            for nodeID in nodeIDList:
                if nodeID not in nodeVNFSupportDict:
                    nodeVNFSupportDict[nodeID] = [vnfType]
                else:
                    if vnfType not in nodeVNFSupportDict[nodeID]:
                        nodeVNFSupportDict[nodeID].append(vnfType)
        return nodeVNFSupportDict

    def addClassifier(self):
        # add classifier for each switch
        for switchID, switchDictInfo in self.switches.items():
            switch = switchDictInfo['switch']
            self.logger.info("addClassifier switchID:{0}".format(
                switchID))
            serverID = self._assignServerID()
            dpIP = self._dhcp.assignClassifierIP(switchID)
            self.logger.debug("serverID:{0} dpIP:{1}".format(serverID, dpIP))
            server = Server("eno1", dpIP, SERVER_TYPE_CLASSIFIER)
            # one NIC per server
            server.setControlNICIP(dpIP)
            # two NIC per server
            # server.setControlNICIP(self._dhcp.assignIP(nodeID))
            ctIP = server.getControlNICIP()
            self.logger.debug("ctIP:{0}".format(ctIP))
            self.logger.debug(
                "addClassifier switchID:{0}, dpIP:{1}, ctIP:{2}".format(
                    switchID, dpIP, ctIP))
            server.setServerID(serverID)
            server.updateResource()
            # intel xeon gold 6230 x2
            server.setCoreNUMADistribution(SERVER_NUMA_CPU_DISTRIBUTION)
            server.setHugepagesTotal(SERVER_NUMA_MEMORY_DISTRIBUTION)
            self.servers[serverID] = {'Active': True,
                'timestamp': datetime.datetime(2020, 10, 27, 0,
                                                2, 39, 408596),
                'server':server,
                'Status':None}

    def addClassifier4LogicalTwoTier(self):
        # hard-code function
        # add servers to nodeID: 1
        nodeID = 1
        self._addServer2Switch(nodeID = nodeID,
                                ctIntfName="br1",
                                ctIP = "192.168.0.194",
                                ctMAC = "18:66:da:86:4c:15",
                                dpIP = "2.2.0.36",
                                dpMAC = "00:1b:21:c0:8f:ae",
                                serverType = SERVER_TYPE_CLASSIFIER,
                                vnfTypeList = []
                            )

    def _assignServerID(self):
        return len(self.servers) + SERVERID_OFFSET

    def saveTopologyPickle(self, filePath):
        df = open(filePath, 'wb')

        topologyDict = {
            "nodeNum": self.nodeNum,
            "linkNum": self.linkNum,
            "vnfLocation": self.vnfLocation,
            "sfcRequestSourceDst": self.sfcRequestSourceDst,
            "links": self.links,
            "switches": self.switches,
            "servers": self.servers
        }

        pickle.dump(topologyDict, df)
        df.close()

    def genTopoNameDict(self):
        self.topoNameDict = {}
        self._addFatTree()
        self._addVL2()
        self._addGeant2012()
        self._addAttMpls()
        self._addSwitchL3()
        return self.topoNameDict

    def _addTriAngle(self):
        self.topoNameDict["triAngle"] = []
        topoName = "triAngle_V=5"
        self.topoNameDict["triAngle"].append(topoName)

    def _addFatTree(self):
        self.topoNameDict["fat-tree"] = []
        for k in [6]:
            for nPoPNum in [2,3,4,5,6]:
                topoName = "fat-tree-k={0}_V={1}_M={2}".format(
                    k, nPoPNum, SFC_REQUEST_NUM)
                self.topoNameDict["fat-tree"].append(topoName)

    def _addVL2(self):
        self.topoNameDict["VL2"] = []
        for intNum in [8]:
            for aggNum in [8]:
                for nPoPNum in [6]:
                    # VL2_int=8_agg=8_V=6.txt
                    topoName = "VL2_int={0}_agg={1}_V={2}_M={3}".format(
                        intNum, aggNum, nPoPNum, SFC_REQUEST_NUM)
                    self.topoNameDict["VL2"].append(topoName)

    def _addPdh(self):
        pass
        # TODO

    def _addGeant(self):
        pass
        # TODO

    def _addFrance(self):
        pass
        # TODO

    def _addGeant2012(self):
        self.topoNameDict["Geant2012"] = []
        for nPoPNum in [6]:
            topoName = "Geant2012_V={0}_M={1}".format(
                nPoPNum, SFC_REQUEST_NUM)
            self.topoNameDict["Geant2012"].append(topoName)

    def _addAttMpls(self):
        self.topoNameDict["AttMpls"] = []
        for nPoPNum in [6]:
            topoName = "AttMpls_V={0}_M={1}".format(
                nPoPNum, SFC_REQUEST_NUM)
            self.topoNameDict["AttMpls"].append(topoName)

    def _addSwitchL3(self):
        self.topoNameDict["SwitchL3"] = []
        for nPoPNum in [6]:
            topoName = "SwitchL3_V={0}_M={1}".format(
                nPoPNum, SFC_REQUEST_NUM)
            self.topoNameDict["SwitchL3"].append(topoName)
