#!/usr/bin/python
# -*- coding: UTF-8 -*-

import copy

from sam.base.path import *
from sam.base.server import *
from sam.base.messageAgent import *
from sam.base.socketConverter import *
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.orchestration.algorithms.multiLayerGraph import *
from sam.orchestration.algorithms.performanceModel import *
from sam.orchestration.algorithms.base.mappingAlgorithmBase import *
from sam.orchestration.algorithms.base.pathServerFiller import *
from sam.orchestration.algorithms.base.failureScenario import *
from sam.orchestration.algorithms.resourceAllocator import *


class MMLBSFC(MappingAlgorithmBase, PathServerFiller):
    def __init__(self, dib, requestList, requestForwardingPathSet):
        self._dib = copy.deepcopy(dib)
        self.requestList = requestList
        self.requestForwardingPathSet = requestForwardingPathSet

        logConfigur = LoggerConfigurator(__name__,
            './log', 'MMLBSFC.log', level='warning')
        self.logger = logConfigur.getLogger()

        self.zoneName = self.requestList[0].attributes['zone']
        self._genRequestIngAndEg()
        self._genAllFailureScenarios()

    def mapSFCI(self):
        self.logger.info("MMLBSFC mapSFCI")
        self._mapBackupPath4AllFailureScenarios()
        return self.requestForwardingPathSet

    def _genAllFailureScenarios(self):
        # node protection: switch and server
        self.scenarioList = []
        for switchesInfoDict in self._dib.getSwitchesByZone(self.zoneName):
            print(switchesInfoDict)
            raw_input()
            for switchID, switchInfoDict in switchesInfoDict.items():
                switch = self._dib.getSwitch(switchID, self.zoneName)
                fS = FailureScenario()
                fS.addElement(switch)
                self.scenarioList.append(fS)

        for serversInfoDict in self._dib.getServersByZone(self.zoneName):
            for serverID, serverInfoDict in serversInfoDict.items():
                server = self._dib.getServer(serverID, self.zoneName)
                fS = FailureScenario()
                fS.addElement(server)
                self.scenarioList.append(fS)

    def _mapBackupPath4AllFailureScenarios(self):
        for scenario in self.scenarioList:
            self._mapBackupPath4Scenario(scenario)

    def _mapBackupPath4Scenario(self, scenario):
        self._init()
        self._allocateResource4UnaffectedPart()
        self._genBackupPath4EachRequest()

    def _init(self):
        self._tmpDib = copy.deepcopy(self.dib)
        self.elementList = scenario.getElementsList()
        self.unaffectedForwardingPathSegDict = {}   # {rIndex: unaffected part of forwardingPath}

    def _allocateResource4UnaffectedPart(self):
        for rIndex in range(len(self.requestList)):
            if not self._isRequestAffectedByFailure(rIndex):
                fp = self._getPrimaryForwardingPath(rIndex)
                self.addForwardingPath2UnaffectedForwardingPathSegDict(rIndex, fp)
            else:
                fp = self._getPrimaryForwardingPath(rIndex)
                segFp = self._getUnaffectedPartOfPrimaryForwardingPath(rIndex, fp)
                self.addForwardingPath2UnaffectedForwardingPathSegDict(rIndex, segFp)

        rA = ResourceAllocator(self._tmpDib)
        rA.allocate4ForwardingPathSet(self.unaffectedForwardingPathSegDict)

    def _genBackupPath4EachRequest(self):
        for rIndex in range(len(self.requestList)):
            self.request = self.requestList[rIndex]
            sfc = self.request.attributes['sfc']
            c = sfc.getSFCLength()

            mlg = MultiLayerGraph()
            mlg.loadInstance4dibAndRequest(self._tmpDib, 
                self.request, WEIGHT_TYPE_DELAY_MODEL)
            mlg.addAbandonNodes([self.elementList])
            mlg.trans2MLG()

            fp = self._getPrimaryForwardingPath(rIndex)
            (layerNum, repairSwitchID) = self._getRepairLayerSwitchTuple(
                fp, self.elementList)
            egSwitchID = self.requestEgSwitchID[rIndex]

            try:
                path = mlg.getPath(layerNum, repairSwitchID, c, egSwitchID)
                path = self._selectNPoPNodeAndServers(path, rIndex)
                self.logger.debug("path:{0}".format(path))
            except Exception as ex:
                ExceptionProcessor(self.logger).logException(ex)
                self.logger.warning(
                    "Can't find valid primary path for request {0}".format(
                        rIndex))
                break



    # def _getPrimaryForwardingPath(self, rIndex):
    #     self.requestForwardingPathSet



