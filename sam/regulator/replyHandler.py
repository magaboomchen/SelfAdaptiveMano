#!/usr/bin/python
# -*- coding: UTF-8 -*-

import math
import time
import uuid

from sam.base.messageAgent import DISPATCHER_QUEUE, MSG_TYPE_REQUEST,\
                                     SAMMessage
from sam.base.request import REQUEST_TYPE_ADD_SFCI, REQUEST_TYPE_DEL_SFCI, \
                            Request
from sam.base.sfc import AUTO_SCALE, REGULATOR_SFCIID_ALLOCATED_RANGE, STATE_ACTIVE, STATE_DELETED, \
                    STATE_SCALING_IN_MODE, SFC, SFCI, STATE_SCALING_OUT_MODE
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.vnf import VNFIStatus
from sam.orchestration.algorithms.base.performanceModel import PerformanceModel
from sam.regulator.config import ENABLE_SCALING, MAX_OVER_LOAD_NUM_THRESHOLD, \
                                    MAX_UNDER_LOAD_NUM_THRESHOLD
from sam.regulator.sfciIDAllocator import SFCIDAllocator

# SFC traffic load state
OVERLOAD_STATE = "OVERLOAD_STATE"
UNDERLOAD_STATE = "UNDERLOAD_STATE"
NORMALLOAD_STATE = "NORMALLOAD_STATE"


class ReplyHandler(object):
    def __init__(self, logger, msgAgent, oib):
        self.logger = logger
        self._messageAgent = msgAgent
        self._oib = oib
        self.sfcisInAllZoneDict = {}
        self.sfcLoadStateDict = {}  # [sfcUUID] = {"loadList": [], "currentSFCINum": 1, "targetSFCINum": 1}
        self.sfciLoadDict = {}      # [sfciID] = [[sloRealTimeValue, timestamp, bandwidth]]
        self.maxLoadListLength = max(MAX_OVER_LOAD_NUM_THRESHOLD, MAX_UNDER_LOAD_NUM_THRESHOLD)
        self.pM = PerformanceModel()
        self.scalingOutTaskDict = {}  # Dict[sfcUUID, Dict[sfciID, taskState]]
        self.scalingInTaskDict = {}  # Dict[sfcUUID, Dict[sfciID, taskState]]
        self.sfciIDAllocator = SFCIDAllocator(self._oib,
                                                REGULATOR_SFCIID_ALLOCATED_RANGE[0],
                                                REGULATOR_SFCIID_ALLOCATED_RANGE[1])

    def handle(self, reply):
        try:
            self.logger.info("Get a reply")
            self.scalingHandler(reply)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, 
                "Regualtor reply handler")
        finally:
            pass

    def scalingHandler(self, reply):
        if not ENABLE_SCALING:
            return
        if "sfcis" in reply.attributes.keys():
            self.logger.info("Get sfcis!")
            self.sfcisInAllZoneDict = reply.attributes["sfcis"]
            # get SFC info from database
            self.sfcTupleList = self._oib.getAllSFC()
            for sfcTuple in self.sfcTupleList:
                self.updateSFCLoad(sfcTuple)
                self.processAbnormalLoadSFC(sfcTuple)

    def updateSFCLoad(self, sfcTuple):
        # compute the input traffic bandwidth of all SFCs
        zoneName = sfcTuple[0]
        sfciIDList = sfcTuple[2]
        sfc = sfcTuple[4]
        self.logger.info("sfciIDList is {0}".format(sfciIDList))
        # self.logger.info("sfc is {0}".format(sfc))
        sumSFCITrafficBandwidth = 0
        for sfciID in sfciIDList:
            # sfci = self._oib.getSFCI4DB(sfciID)
            sfciState = self._oib.getSFCIState(sfciID)
            if (sfciState == STATE_ACTIVE 
                and sfciID in self.sfcisInAllZoneDict[zoneName]):
                sfci = self.sfcisInAllZoneDict[zoneName][sfciID]
                # self.logger.warning("sfci is {0}".format(sfci))
                sfciTrafficBandwidth = self.updateSFCILoad(sfci)
                sumSFCITrafficBandwidth += sfciTrafficBandwidth

        self.logger.debug("sumSFCITrafficBandwidth is {0}".format(sumSFCITrafficBandwidth))
        targetSFCINum = self.computeTargetSFCINum(sfc, sumSFCITrafficBandwidth)
        self.logger.debug("targetSFCINum is {0}".format(targetSFCINum))
        currentSFCINum = len(sfciIDList)
        if currentSFCINum > targetSFCINum:
            loadState = UNDERLOAD_STATE
        elif currentSFCINum == targetSFCINum:
            loadState = NORMALLOAD_STATE
        elif currentSFCINum < targetSFCINum:
            loadState = OVERLOAD_STATE

        if sfc.sfcUUID not in self.sfcLoadStateDict:
            self.sfcLoadStateDict[sfc.sfcUUID] = {"loadList": [],
                                                    "currentSFCINum": 1,
                                                    "targetSFCINum": 1}
        loadList = self.sfcLoadStateDict[sfc.sfcUUID]["loadList"]
        loadList.append(loadState)
        if len(loadList) > self.maxLoadListLength:
            loadList.pop(0)
        self.sfcLoadStateDict[sfc.sfcUUID]["currentSFCINum"] = currentSFCINum
        self.sfcLoadStateDict[sfc.sfcUUID]["targetSFCINum"] = targetSFCINum

    def updateSFCILoad(self, sfci):
        sfciID = sfci.sfciID
        if sfciID not in self.sfciLoadDict:
            self.sfciLoadDict[sfciID] = []
        sumVNFIsStatus = self.computeFirstVNFIsLoad(sfci.vnfiSequence)
        self.sfciLoadDict[sfciID].append([sumVNFIsStatus, time.time(), 0])
        if len(self.sfciLoadDict[sfciID]) >= 2:
            trafficLoad1 = self.sfciLoadDict[sfciID][-1][0].inputTrafficAmount
            trafficLoad0 = self.sfciLoadDict[sfciID][-2][0].inputTrafficAmount
            timestamp1 = self.sfciLoadDict[sfciID][-1][1]
            timestamp0 = self.sfciLoadDict[sfciID][-2][1]
            if trafficLoad0 != None and trafficLoad1 != None:
                deltaT = (trafficLoad1 - trafficLoad0) * 1.0 / 1e06
                self.sfciLoadDict[sfciID][-1][2] = deltaT / (timestamp1 - timestamp0)
        if len(self.sfciLoadDict[sfciID]) > self.maxLoadListLength:
            self.sfciLoadDict[sfciID].pop(0)
        self.logger.info("self.sfciLoadDict of {0} is {1}".format(sfciID, 
                                                self.sfciLoadDict[sfciID]))
        return self.sfciLoadDict[sfciID][-1][2]

    def computeFirstVNFIsLoad(self, vnfiSequence):
        sumVNFIsStatus = VNFIStatus(inputTrafficAmount=0,
                                    inputPacketAmount=0,
                                    outputTrafficAmount=0,
                                    outputPacketAmount=0)
        for vnfi in vnfiSequence[0]:
            if type(vnfi.vnfiStatus) != VNFIStatus:
                continue
            if vnfi.vnfiStatus.inputTrafficAmount != None:
                sumVNFIsStatus.inputTrafficAmount += vnfi.vnfiStatus.inputTrafficAmount
            if vnfi.vnfiStatus.inputPacketAmount != None:
                sumVNFIsStatus.inputPacketAmount += vnfi.vnfiStatus.inputPacketAmount
            if vnfi.vnfiStatus.outputTrafficAmount != None:
                sumVNFIsStatus.outputTrafficAmount += vnfi.vnfiStatus.outputTrafficAmount
            if vnfi.vnfiStatus.outputPacketAmount != None:
                sumVNFIsStatus.outputPacketAmount += vnfi.vnfiStatus.outputPacketAmount
        self.logger.debug("sumVNFIsStatus is {0}".format(sumVNFIsStatus))
        return sumVNFIsStatus

    def computeTargetSFCINum(self, sfc, sumSFCITrafficBandwidth):
        vNFTypeSequence = sfc.vNFTypeSequence
        maxExpCPU = 0
        maxExpMem = 0
        maxExpBW = 0
        for vnfType in vNFTypeSequence:
            (expCPU, expMem, expBW) = self.pM.getExpectedServerResource(
                                        vnfType, sumSFCITrafficBandwidth)
            maxExpCPU = max(maxExpCPU, expCPU)
            maxExpMem = max(maxExpMem, expMem)
            maxExpBW = max(maxExpBW, expBW)
        vnfiResourceQuota = sfc.vnfiResourceQuota
        quotaCPU = vnfiResourceQuota["cpu"]
        quotaMem = vnfiResourceQuota["mem"]
        targetSFCINum = math.ceil(maxExpCPU / quotaCPU)
        targetSFCINum = max(math.ceil(maxExpMem / quotaMem), targetSFCINum)
        targetSFCINum = max(1, targetSFCINum)
        return targetSFCINum 

    def processAbnormalLoadSFC(self, sfcTuple):
        sfc = sfcTuple[4]

        if self.isOverLoadCondition(sfc):
            self._oib.updateSFCState(sfc.sfcUUID, STATE_SCALING_OUT_MODE)
            self.scalingOutSFC(sfc)
            return

        if self.isUnderLoadCondition(sfc):
            self._oib.updateSFCState(sfc.sfcUUID, STATE_SCALING_IN_MODE)
            self.scalingInSFC(sfc)
            return 

    def isOverLoadCondition(self, sfc):
        currentSFCINum = self.sfcLoadStateDict[sfc.sfcUUID]["currentSFCINum"]
        maxScalingInstanceNumber = sfc.maxScalingInstanceNumber
        scalingOutCondition = (currentSFCINum < maxScalingInstanceNumber)

        loadList = self.sfcLoadStateDict[sfc.sfcUUID]["loadList"]
        self.logger.debug("loadList is {0}".format(loadList))
        overLoadCnt = 0
        for load in loadList:
            if load == OVERLOAD_STATE:
                overLoadCnt += 1
        scalingOutCondition = scalingOutCondition \
                                and (overLoadCnt >= MAX_OVER_LOAD_NUM_THRESHOLD)

        sfcState = self._oib.getSFCState(sfc.sfcUUID)
        scalingOutCondition = scalingOutCondition and (sfcState == STATE_ACTIVE)
        for sfcLoadState in loadList[-MAX_OVER_LOAD_NUM_THRESHOLD:]:
            scalingOutCondition = scalingOutCondition \
                                    and (sfcLoadState == OVERLOAD_STATE) \
                                    and (sfc.scalingMode == AUTO_SCALE)
        return scalingOutCondition

    def isUnderLoadCondition(self, sfc):
        loadList = self.sfcLoadStateDict[sfc.sfcUUID]["loadList"]
        self.logger.debug("loadList is {0}".format(loadList))
        underLoadCnt = 0
        for load in loadList:
            if load == UNDERLOAD_STATE:
                underLoadCnt += 1
        scalingInCondition = (underLoadCnt >= MAX_UNDER_LOAD_NUM_THRESHOLD)        

        sfcState = self._oib.getSFCState(sfc.sfcUUID)
        scalingInCondition = scalingInCondition and (sfcState == STATE_ACTIVE)
        for sfcLoadState in loadList[-MAX_UNDER_LOAD_NUM_THRESHOLD:]:
            scalingInCondition = scalingInCondition \
                                    and (sfcLoadState == UNDERLOAD_STATE)  \
                                    and (sfc.scalingMode == AUTO_SCALE)
        return scalingInCondition

    def scalingOutSFC(self, sfc):
        deltaSFCINum = abs(self.getDeltaSFCINum(sfc))
        self.logger.warning("scaling out deltaSFCINum {0}".format(deltaSFCINum))
        for _ in range(deltaSFCINum):
            sfciID = self.sfciIDAllocator.getDeletedStateSFCIID(sfc)
            if sfciID == None:
                sfciID = self.sfciIDAllocator.getAvaSFCIID()
            sfci = SFCI(sfciID)
            req = self._genAddSFCIRequest(sfc, sfci)
            self._sendRequest2Dispatcher(req)
            if sfc.sfcUUID not in self.scalingOutTaskDict:
                self.scalingOutTaskDict[sfc.sfcUUID] = {}
            self.scalingOutTaskDict[sfc.sfcUUID] = {sfciID: "adding"}

    def _genAddSFCIRequest(self, sfc, sfci):
        req = Request(0, uuid.uuid1(), REQUEST_TYPE_ADD_SFCI, 
                        attributes={
                            "sfc": sfc,
                            "sfci": sfci
                    })
        return req

    def _sendRequest2Dispatcher(self, request):
        queueName = DISPATCHER_QUEUE
        msg = SAMMessage(MSG_TYPE_REQUEST, request)
        self._messageAgent.sendMsg(queueName, msg)

    def getDeltaSFCINum(self, sfc):
        maxScalingInstanceNumber = sfc.maxScalingInstanceNumber
        targetSFCINum = self.sfcLoadStateDict[sfc.sfcUUID]["targetSFCINum"]
        targetSFCINum = min(targetSFCINum, maxScalingInstanceNumber)
        targetSFCINum = max(targetSFCINum, 1)
        currentSFCINum = self.sfcLoadStateDict[sfc.sfcUUID]["currentSFCINum"]
        deltaSFCINum = targetSFCINum - currentSFCINum
        return deltaSFCINum

    def scalingInSFC(self, sfc):
        deltaSFCINum = abs(self.getDeltaSFCINum(sfc))
        self.logger.warning("scaling in deltaSFCINum {0}".format(deltaSFCINum))
        sfciIDList = self._oib.getSFCCorrespondingSFCIID4DB(sfc.sfcUUID)
        sfciIDList = sorted(sfciIDList)
        for sfciID in sfciIDList[:deltaSFCINum]:
            sfci = self._oib.getSFCI4DB(sfciID)
            req = self._genDelSFCIRequest(sfci)
            self._sendRequest2Dispatcher(req)
            if sfc.sfcUUID not in self.scalingInTaskDict:
                self.scalingInTaskDict[sfc.sfcUUID] = {}
            self.scalingOutTaskDict[sfc.sfcUUID] = {sfciID: "deleting"}

    def _genDelSFCIRequest(self, sfci):
        req = Request(0, uuid.uuid1(), REQUEST_TYPE_DEL_SFCI, 
                        attributes={
                            "sfci": sfci
                    })
        return req

    def processAllScalingTasks(self):
        self.logger.debug(" Scaling out task dict is {0}".format(self.scalingOutTaskDict))
        time.sleep(1)
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
