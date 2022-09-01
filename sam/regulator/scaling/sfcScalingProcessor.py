#!/usr/bin/python
# -*- coding: UTF-8 -*-

import math
import uuid
from typing import Dict, List, Union

from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.messageAgent import DISPATCHER_QUEUE, MSG_TYPE_REQUEST, \
                                SIMULATOR_ZONE, TURBONET_ZONE, MessageAgent,\
                                SAMMessage
from sam.base.request import REQUEST_TYPE_ADD_SFCI, REQUEST_TYPE_DEL_SFCI, \
                            Request
from sam.base.sfc import SFC, SFCI
from sam.base.command import CommandReply
from sam.base.sfcConstant import AUTO_SCALE, REGULATOR_SFCIID_ALLOCATED_RANGE, SFC_DIRECTION_0, SFC_DIRECTION_1, \
                    STATE_ACTIVE, STATE_DELETED, STATE_IN_PROCESSING, \
                    STATE_SCALING_IN_MODE, STATE_SCALING_OUT_MODE
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.vnfiStatus import VNFIStatus
from sam.base.vnf import VNFI, PREFERRED_DEVICE_TYPE_P4, PREFERRED_DEVICE_TYPE_SERVER
from sam.orchestration.algorithms.base.performanceModel import PerformanceModel
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer
from sam.regulator.config import ENABLE_SCALING, MAX_OVER_LOAD_NUM_THRESHOLD, \
                                    MAX_UNDER_LOAD_NUM_THRESHOLD
from sam.regulator.sfciIDAllocator import SFCIDAllocator

# SFC traffic load state
OVERLOAD_STATE = "OVERLOAD_STATE"
UNDERLOAD_STATE = "UNDERLOAD_STATE"
NORMALLOAD_STATE = "NORMALLOAD_STATE"
STARTUP_STATE = "STARTUP_STATE"

SCALING_TASK_STATE_ADDING = "SCALING_TASK_STATE_ADDING"
SCALING_TASK_STATE_DELETING = "SCALING_TASK_STATE_DELETING"


class SFCScalingProcessor(object):
    def __init__(self, msgAgent, oib):
        # type: (MessageAgent, OrchInfoBaseMaintainer) -> None
        logConfigur = LoggerConfigurator(__name__, './log',
            'SFCScalingProcessor.log',
            level='debug')
        self.logger = logConfigur.getLogger()
        self._messageAgent = msgAgent
        self._oib = oib
        self.sfcisInAllZoneDict = {}
        self.sfcLoadStateDict = {}  # [sfcUUID] = {"loadList": [], "currentValidSFCINum": 1, "targetSFCINum": 1}
        self.sfciLoadDict = {}      # [sfciID] = [[sloRealTimeValue, timestamp, bandwidth]]
        self.maxLoadListLength = max(MAX_OVER_LOAD_NUM_THRESHOLD, 
                                        MAX_UNDER_LOAD_NUM_THRESHOLD)
        self.pM = PerformanceModel()
        self.scalingOutTaskDict = {}  # type: Dict[SFC.sfcUUID, Dict[SFCI.sfciID, Union[OVERLOAD_STATE, UNDERLOAD_STATE, NORMALLOAD_STATE, STARTUP_STATE]]]
        self.scalingInTaskDict = {}  # type: Dict[SFC.sfcUUID, Dict[SFCI.sfciID, Union[OVERLOAD_STATE, UNDERLOAD_STATE, NORMALLOAD_STATE, STARTUP_STATE]]]
        self.sfciIDAllocator = SFCIDAllocator(self._oib,
                                    REGULATOR_SFCIID_ALLOCATED_RANGE[0],
                                    REGULATOR_SFCIID_ALLOCATED_RANGE[1])

    def handle(self, reply):
        # type: (CommandReply) -> None
        try:
            self.logger.info("Get a reply")
            self.scalingHandler(reply)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, 
                "Regualtor reply handler")
        finally:
            pass

    def scalingHandler(self, reply):
        # type: (CommandReply) -> None
        if not ENABLE_SCALING:
            return
        if "sfcis" in reply.attributes.keys():
            self.logger.info("Get sfcis!")
            self.sfcisInAllZoneDict = reply.attributes["sfcis"]
            # get SFC info from database
            self.sfcTupleList = self._oib.getAllSFC()
            if self.sfcTupleList != None:
                for sfcTuple in self.sfcTupleList:
                    self.updateSFCLoad(sfcTuple)
                    self.processAbnormalLoadSFC(sfcTuple)

    def updateSFCLoad(self, sfcTuple):
        # compute the input traffic bandwidth of all SFCs
        zoneName = sfcTuple[0]
        sfciIDList = sfcTuple[2]
        sfc = sfcTuple[4]   # type: SFC
        self.logger.info("sfciIDList is {0}".format(sfciIDList))
        # self.logger.info("sfc is {0}".format(sfc))
        sumSFCITrafficBandwidth = 0
        for sfciID in sfciIDList:
            # sfci = self._oib.getSFCI4DB(sfciID)
            sfciState = self._oib.getSFCIState(sfciID)
            if zoneName not in self.sfcisInAllZoneDict.keys():
                self.sfcisInAllZoneDict[zoneName] = {}
            if (sfciState == STATE_ACTIVE 
                    and sfciID in self.sfcisInAllZoneDict[zoneName]):
                sfci = self.sfcisInAllZoneDict[zoneName][sfciID]
                # self.logger.warning("sfci is {0}".format(sfci))
                sfciTrafficBandwidth = self.updateSFCILoad(sfci)
                sumSFCITrafficBandwidth += sfciTrafficBandwidth

        self.logger.debug("sumSFCITrafficBandwidth is {0} Gbps".format(sumSFCITrafficBandwidth))
        targetSFCINum = self.computeTargetSFCINum(sfc, sumSFCITrafficBandwidth)
        self.logger.debug("targetSFCINum is {0}".format(targetSFCINum))
        currentValidSFCINum = self.getCurrentValidSFCINum(sfciIDList)
        self.logger.debug("currentValidSFCINum is {0}".format(currentValidSFCINum))
        # if currentValidSFCINum != 0:
        #     if currentValidSFCINum > targetSFCINum:
        #         loadState = UNDERLOAD_STATE
        #     elif currentValidSFCINum == targetSFCINum:
        #         loadState = NORMALLOAD_STATE
        #     elif currentValidSFCINum < targetSFCINum:
        #         loadState = OVERLOAD_STATE
        # else:
        #     loadState = STARTUP_STATE
        if currentValidSFCINum > targetSFCINum:
            loadState = UNDERLOAD_STATE
        elif currentValidSFCINum == targetSFCINum:
            loadState = NORMALLOAD_STATE
        elif currentValidSFCINum < targetSFCINum:
            loadState = OVERLOAD_STATE

        if sfc.sfcUUID not in self.sfcLoadStateDict:
            self.sfcLoadStateDict[sfc.sfcUUID] = {"loadList": [],
                                                    "currentValidSFCINum": 0,
                                                    "targetSFCINum": 0}
        loadList = self.sfcLoadStateDict[sfc.sfcUUID]["loadList"]
        loadList.append(loadState)
        if len(loadList) > self.maxLoadListLength:
            loadList.pop(0)
        self.sfcLoadStateDict[sfc.sfcUUID]["currentValidSFCINum"] = currentValidSFCINum
        self.sfcLoadStateDict[sfc.sfcUUID]["targetSFCINum"] = targetSFCINum

    def getCurrentValidSFCINum(self, sfciIDList):
        cnt = 0
        for sfciID in sfciIDList:
            sfciState = self._oib.getSFCIState(sfciID)
            if sfciState in [STATE_ACTIVE, STATE_IN_PROCESSING]:
                cnt += 1
        return cnt

    def updateSFCILoad(self, sfci):
        # type: (SFCI) -> float
        sfciID = sfci.sfciID
        if sfciID not in self.sfciLoadDict:
            self.sfciLoadDict[sfciID] = []
        sumVNFIsStatus = self.computeFirstVNFIsLoad(sfci.vnfiSequence)
        self.sfciLoadDict[sfciID].append([sumVNFIsStatus, 
                                            sumVNFIsStatus.timestamp.timestamp(),
                                            0])
        if len(self.sfciLoadDict[sfciID]) >= 2:
            trafficLoad1 = 0
            trafficLoad0 = 0
            for directionID in [SFC_DIRECTION_0, SFC_DIRECTION_1]:
                trafficLoad1 += self.sfciLoadDict[sfciID][-1][0].inputTrafficAmount[directionID]
                trafficLoad0 += self.sfciLoadDict[sfciID][-2][0].inputTrafficAmount[directionID]
            timestamp1 = self.sfciLoadDict[sfciID][-1][1]
            timestamp0 = self.sfciLoadDict[sfciID][-2][1]
            if trafficLoad0 != None and trafficLoad1 != None:
                deltaLoad = (trafficLoad1 - trafficLoad0) * 1.0 / 1e03
                deltaTime = timestamp1 - timestamp0
                if deltaTime > 0:
                    self.sfciLoadDict[sfciID][-1][2] = deltaLoad / deltaTime
                else:
                    self.sfciLoadDict[sfciID].pop(0)
        if len(self.sfciLoadDict[sfciID]) > self.maxLoadListLength:
            self.sfciLoadDict[sfciID].pop(0)
        self.logger.info("self.sfciLoadDict of {0} is {1}".format(sfciID, 
                                                self.sfciLoadDict[sfciID]))
        return self.sfciLoadDict[sfciID][-1][2]

    def computeFirstVNFIsLoad(self, vnfiSequence):
        # type: (List[List[VNFI]]) -> VNFIStatus
        sumVNFIsStatus = VNFIStatus(inputTrafficAmount={SFC_DIRECTION_0:0, SFC_DIRECTION_1:0},
                                    inputPacketAmount={SFC_DIRECTION_0:0, SFC_DIRECTION_1:0},
                                    outputTrafficAmount={SFC_DIRECTION_0:0, SFC_DIRECTION_1:0},
                                    outputPacketAmount={SFC_DIRECTION_0:0, SFC_DIRECTION_1:0})
        for vnfi in vnfiSequence[0]:
            if type(vnfi.vnfiStatus) != VNFIStatus:
                continue
            self.logger.warning("vnfi.vnfiStatus {0}".format(vnfi.vnfiStatus))
            for directionID in [SFC_DIRECTION_0, SFC_DIRECTION_1]:
                if vnfi.vnfiStatus.inputTrafficAmount != None:
                    sumVNFIsStatus.inputTrafficAmount[directionID] += vnfi.vnfiStatus.inputTrafficAmount[directionID]
                if vnfi.vnfiStatus.inputPacketAmount != None:
                    sumVNFIsStatus.inputPacketAmount[directionID] += vnfi.vnfiStatus.inputPacketAmount[directionID]
                if vnfi.vnfiStatus.outputTrafficAmount != None:
                    sumVNFIsStatus.outputTrafficAmount[directionID] += vnfi.vnfiStatus.outputTrafficAmount[directionID]
                if vnfi.vnfiStatus.outputPacketAmount != None:
                    sumVNFIsStatus.outputPacketAmount[directionID] += vnfi.vnfiStatus.outputPacketAmount[directionID]
        self.logger.debug("sumVNFIsStatus is {0}".format(sumVNFIsStatus))
        return sumVNFIsStatus

    def computeTargetSFCINum(self, sfc, sumSFCITrafficBandwidth):
        # type: (SFC, int) -> int
        # Gbps
        vNFTypeSequence = sfc.vNFTypeSequence
        maxExpCPU = 0
        maxExpMem = 0
        for idx,vnfType in enumerate(vNFTypeSequence):
            pDT = sfc.vnfSequence[idx].preferredDeviceType
            if pDT == PREFERRED_DEVICE_TYPE_P4:
                maxExpCPU = 0
                maxExpMem = 0
            elif pDT == PREFERRED_DEVICE_TYPE_SERVER:
                (expCPU, expMem, expBW) = self.pM.getExpectedServerResource(
                                            vnfType, sumSFCITrafficBandwidth)
                maxExpCPU = max(maxExpCPU, expCPU)
                maxExpMem = max(maxExpMem, expMem)
        vnfiResourceQuota = sfc.vnfiResourceQuota
        quotaCPU = vnfiResourceQuota["cpu"]
        quotaMem = vnfiResourceQuota["mem"]
        targetSFCINum = math.ceil(maxExpCPU / quotaCPU)
        targetSFCINum = max(math.ceil(maxExpMem / quotaMem), targetSFCINum)
        targetSFCINum = max(1, targetSFCINum)
        return targetSFCINum 

    def processAbnormalLoadSFC(self, sfcTuple):
        sfc = sfcTuple[4]   # type: (SFC)

        if self.isOverLoadCondition(sfc):
            self._oib.updateSFCState(sfc.sfcUUID, STATE_SCALING_OUT_MODE)
            self.scalingOutSFC(sfc)
            return

        if self.isUnderLoadCondition(sfc):
            self._oib.updateSFCState(sfc.sfcUUID, STATE_SCALING_IN_MODE)
            self.scalingInSFC(sfc)
            return 

    def isOverLoadCondition(self, sfc):
        # type: (SFC) -> bool
        currentValidSFCINum = self.sfcLoadStateDict[sfc.sfcUUID]["currentValidSFCINum"]
        maxScalingInstanceNumber = sfc.maxScalingInstanceNumber
        scalingOutCondition = (currentValidSFCINum < maxScalingInstanceNumber)

        sfcState = self._oib.getSFCState(sfc.sfcUUID)
        scalingOutCondition = scalingOutCondition \
                                and (sfcState == STATE_ACTIVE) \
                                and (sfc.scalingMode == AUTO_SCALE)

        loadList = self.sfcLoadStateDict[sfc.sfcUUID]["loadList"]
        # self.logger.debug("loadList is {0}".format(loadList))
        # overLoadCnt = 0
        # for load in loadList:
        #     if load == OVERLOAD_STATE:
        #         overLoadCnt += 1
        # scalingOutCondition = scalingOutCondition \
        #                         and (overLoadCnt >= MAX_OVER_LOAD_NUM_THRESHOLD) \

        scalingOutConditionPart1 = True
        for sfcLoadState in loadList[-MAX_OVER_LOAD_NUM_THRESHOLD:]:
            scalingOutConditionPart1 = scalingOutConditionPart1 \
                                    and (sfcLoadState == OVERLOAD_STATE) \

        scalingOutConditionPart2 = (currentValidSFCINum == 0)

        scalingOutCondition = scalingOutCondition \
                and (scalingOutConditionPart1 or scalingOutConditionPart2)

        return scalingOutCondition

    def isUnderLoadCondition(self, sfc):
        # type: (SFC) -> bool
        sfcState = self._oib.getSFCState(sfc.sfcUUID)
        scalingInCondition = (sfcState == STATE_ACTIVE)

        loadList = self.sfcLoadStateDict[sfc.sfcUUID]["loadList"]
        self.logger.debug("loadList is {0}".format(loadList))
        # underLoadCnt = 0
        # for load in loadList:
        #     if load == UNDERLOAD_STATE:
        #         underLoadCnt += 1
        # scalingInCondition = (underLoadCnt >= MAX_UNDER_LOAD_NUM_THRESHOLD)
        for sfcLoadState in loadList[-MAX_UNDER_LOAD_NUM_THRESHOLD:]:
            scalingInCondition = scalingInCondition \
                                    and (sfcLoadState == UNDERLOAD_STATE)  \
                                    and (sfc.scalingMode == AUTO_SCALE)
        return scalingInCondition

    def scalingOutSFC(self, sfc):
        # type: (SFC) -> None
        deltaSFCINum = abs(self.getDeltaSFCINum(sfc))
        self.logger.warning("scaling out deltaSFCINum {0}".format(deltaSFCINum))
        for _ in range(deltaSFCINum):
            sfciID = self.sfciIDAllocator.getDeletedStateSFCIID(sfc)
            if sfciID == None:
                sfciID = self.sfciIDAllocator.getAvaSFCIID()
            sfci = SFCI(sfciID)
            zoneName = self._oib.getSFCZone4DB(sfc.sfcUUID)
            req = self._genAddSFCIRequest(sfc, sfci, zoneName)
            self._sendRequest2Dispatcher(req)
            if sfc.sfcUUID not in self.scalingOutTaskDict:
                self.scalingOutTaskDict[sfc.sfcUUID] = {}
            self.scalingOutTaskDict[sfc.sfcUUID] = {sfciID: SCALING_TASK_STATE_ADDING}

    def _genAddSFCIRequest(self, sfc, sfci, zoneName):
        req = Request(0, uuid.uuid1(), REQUEST_TYPE_ADD_SFCI, 
                        attributes={
                            "sfc": sfc,
                            "sfci": sfci,
                            "zone": zoneName
                    })
        return req

    def _sendRequest2Dispatcher(self, request):
        # type: (Request) -> None
        queueName = DISPATCHER_QUEUE
        msg = SAMMessage(MSG_TYPE_REQUEST, request)
        self._messageAgent.sendMsg(queueName, msg)

    def getDeltaSFCINum(self, sfc):
        # type: (SFC) -> int
        maxScalingInstanceNumber = sfc.maxScalingInstanceNumber
        targetSFCINum = self.sfcLoadStateDict[sfc.sfcUUID]["targetSFCINum"]
        targetSFCINum = min(targetSFCINum, maxScalingInstanceNumber)
        targetSFCINum = max(targetSFCINum, 1)
        currentValidSFCINum = self.sfcLoadStateDict[sfc.sfcUUID]["currentValidSFCINum"]
        deltaSFCINum = targetSFCINum - currentValidSFCINum
        return deltaSFCINum

    def scalingInSFC(self, sfc):
        # type: (SFC) -> None
        deltaSFCINum = abs(self.getDeltaSFCINum(sfc))
        self.logger.warning("scaling in deltaSFCINum {0}".format(deltaSFCINum))
        sfciIDList = self._oib.getSFCIIDListOfASFC4DB(sfc.sfcUUID)
        sfciIDList = sorted(sfciIDList)
        zoneName = self._oib.getSFCZone4DB(sfc.sfcUUID)
        for sfciID in sfciIDList[:deltaSFCINum]:
            sfci = self._oib.getSFCI4DB(sfciID)
            req = self._genDelSFCIRequest(sfc, sfci, zoneName)
            self._sendRequest2Dispatcher(req)
            if sfc.sfcUUID not in self.scalingInTaskDict:
                self.scalingInTaskDict[sfc.sfcUUID] = {}
            self.scalingOutTaskDict[sfc.sfcUUID] = {sfciID: SCALING_TASK_STATE_DELETING}

    def _genDelSFCIRequest(self, sfc, sfci, zoneName):
        # type: (SFC, SFCI, Union[SIMULATOR_ZONE, TURBONET_ZONE]) -> Request
        req = Request(0, uuid.uuid1(), REQUEST_TYPE_DEL_SFCI, 
                        attributes={
                            "sfc": sfc,
                            "sfci": sfci,
                            "zone": zoneName
                    })
        return req

    def processAllScalingTasks(self):
        self.logger.debug(" Scaling out task dict is {0}".format(self.scalingOutTaskDict))
        for sfcUUID in list(self.scalingOutTaskDict.keys()):
            isScalingOutFinish = True
            for sfciID, scalingOutTaskState in list(self.scalingOutTaskDict[sfcUUID].items()):
                sfciState = self._oib.getSFCIState(sfciID)
                isScalingOutFinish = (isScalingOutFinish and (sfciState == STATE_ACTIVE))
            if isScalingOutFinish:
                self._oib.updateSFCState(sfcUUID, STATE_ACTIVE)
                del self.scalingOutTaskDict[sfcUUID]

        self.logger.debug(" Scaling in task dict is {0}".format(self.scalingInTaskDict))
        for sfcUUID in list(self.scalingInTaskDict.keys()):
            isScalingInFinish = True
            for sfciID, scalingInTaskState in list(self.scalingInTaskDict[sfcUUID].items()):
                sfciState = self._oib.getSFCIState(sfciID)
                isScalingInFinish = (isScalingInFinish and (sfciState == STATE_DELETED))
            if isScalingInFinish:
                self._oib.updateSFCState(sfcUUID, STATE_ACTIVE)
                del self.scalingInTaskDict[sfcUUID]
