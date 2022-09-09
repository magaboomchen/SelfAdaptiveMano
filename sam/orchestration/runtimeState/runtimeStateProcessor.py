#!/usr/bin/python
# -*- coding: UTF-8 -*-

import copy
from typing import Dict, Union

import networkx as nx

from sam.base.command import CMD_STATE_SUCCESSFUL, CMD_TYPE_ORCHESTRATION_MANAGER_UPDATE_STATE, Command, CommandReply
from sam.base.link import Link
from sam.base.messageAgent import SIMULATOR_ZONE, TURBONET_ZONE
from sam.base.switch import SWITCH_TYPE_DCNGATEWAY
from sam.measurement.dcnInfoBaseMaintainer import DCNInfoBaseMaintainer
from sam.orchestration.runtimeState.runtimeState import RuntimeState


class RuntimeStateProcessor(object):
    def __init__(self, orchestrationName, dib, zoneName):
        # type: (str, DCNInfoBaseMaintainer, Union[SIMULATOR_ZONE, TURBONET_ZONE]) -> None
        self.orchestrationName = orchestrationName
        self.runtimeState = RuntimeState()
        self._dib = dib
        self.graph = None
        self.zoneName = zoneName

    def updateEquipmentState(self, detectionDict):
        # type: (Dict) -> bool
        isEquipmentUpdated = False
        for caseType, equipmentDict in detectionDict.items():
            if caseType in ["failure", "abnormal"]:
                state = False
            elif caseType in ["resume"]:
                state = True
            else:
                raise ValueError("Unknown caseType {0}".format(caseType))

            switchIDList = equipmentDict["switchIDList"]
            for switchID in switchIDList:
                if self._dib.hasSwitch(switchID, self.zoneName):
                    self._dib.updateSwitchState(switchID, self.zoneName, state = state)
                    isEquipmentUpdated = True

            serverIDList = equipmentDict["serverIDList"]
            for serverID in serverIDList:
                if self._dib.hasServer(serverID, self.zoneName):
                    self._dib.updateServerState(serverID, self.zoneName, state = state)
                    isEquipmentUpdated = True

            linkIDList = equipmentDict["linkIDList"]
            for linkID in linkIDList:
                if self._dib.hasLink(linkID[0], linkID[1], self.zoneName):
                    self._dib.updateLinkState(linkID, self.zoneName, state = state)
                    isEquipmentUpdated = True

        return isEquipmentUpdated

    def computeRuntimeState(self):
        # connection detection
        self.transDib2Graph()
        isGraphConnected = nx.is_weakly_connected(copy.deepcopy(self.graph))
        self.runtimeState.setDisconnectionState(isGraphConnected)
        
        # classifier liveness
        switchList = self._dib.getSpecificTypeOfSwitchByZone(self.zoneName, SWITCH_TYPE_DCNGATEWAY)
        if len(switchList) == 0:
            self.runtimeState.setClassifierUnavailableState(True)
        else:
            self.runtimeState.setClassifierUnavailableState(False)

        # resource usage
        pass
        # TODO: why we copy dib in MMLPSFC algorithm?
        # 80% resource water line

    def transDib2Graph(self):
        self.graph = nx.DiGraph()
        edgeList = []

        linksInfoDict = self._dib.getLinksByZone(self.zoneName, pruneInactiveLinks=True)
        for key, linkInfoDict in linksInfoDict.items():
            link = linkInfoDict['link'] # type: Link
            srcNodeID = link.srcID
            dstNodeID = link.dstID
            if (self._dib.isServerID(srcNodeID) 
                    or self._dib.isServerID(dstNodeID)):
                continue
            if not (self._dib.isSwitchActive(srcNodeID, self.zoneName) 
                        and self._dib.isSwitchActive(dstNodeID, self.zoneName)):
                continue
            weight = 1
            edgeList.append((srcNodeID, dstNodeID, weight))
        self.graph.add_weighted_edges_from(edgeList)

    def genFailureAbnormalDetectionNoticeCmdRply(self, cmdID, runtimeState):
        attr = {
            "runtimeState": runtimeState,
            "orchestrationName": self.orchestrationName,
            "zoneName": self.zoneName
        }
        cmdRply = CommandReply(cmdID, CMD_STATE_SUCCESSFUL, attr)
        return cmdRply

    def isSameRuntimeState(self, runtimeState):
        return self.runtimeState == runtimeState

    def updateByNewDib(self, newDib):
        self._dib.updateByNewDib(newDib)
