#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
Input: recieve failure/abnormal notification command from inteligent module
Output: send del/add SFCI request to dispatcher

Get SFCI from db, check which switch/server has been used for each SFCI.

"""

import time
import uuid

from sam.base.command import CMD_TYPE_HANDLE_FAILURE_ABNORMAL
from sam.base.path import DIRECTION1_PATHID_OFFSET, DIRECTION2_PATHID_OFFSET
from sam.base.pickleIO import PickleIO
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.messageAgent import DISPATCHER_QUEUE, MSG_TYPE_REGULATOR_CMD, MSG_TYPE_REQUEST, \
                                REGULATOR_QUEUE, MessageAgent, SAMMessage
from sam.base.request import REQUEST_STATE_FAILED, REQUEST_STATE_IN_PROCESSING, \
                                REQUEST_TYPE_ADD_SFC, REQUEST_TYPE_ADD_SFCI, \
                                REQUEST_TYPE_DEL_SFC, REQUEST_TYPE_DEL_SFCI, \
                                REQUEST_TYPE_GET_DCN_INFO, Request
from sam.base.sfc import STATE_ACTIVE
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer
from sam.regulator.argParser import ArgParser
from sam.regulator.config import FAILURE_REQUEST_RETRY_TIMEOUT, MAX_RETRY_NUM


class Regulator(object):
    def __init__(self):
        self.pIO = PickleIO()
        self._oib = OrchInfoBaseMaintainer("localhost", "dbAgent", "123",
                                            False)
        logConfigur = LoggerConfigurator(__name__, './log',
            'regulator.log',
            level='debug')
        self.logger = logConfigur.getLogger()
        self.regulatorQueueName = REGULATOR_QUEUE
        self._messageAgent = MessageAgent(self.logger)
        self._messageAgent.startRecvMsg(self.regulatorQueueName)
        self.enableRetryFailureRequest = False

    def startRegulator(self):
        self.startRoutine()

    def startRoutine(self):
        try:
            prevTimestamp = time.time()
            while True:
                currTimestamp = time.time()
                deltTimestamp = currTimestamp - prevTimestamp
                if deltTimestamp > FAILURE_REQUEST_RETRY_TIMEOUT:
                    prevTimestamp = time.time()
                    if self.enableRetryFailureRequest:
                        self.retryFailureRequests()
                msgCnt = self._messageAgent.getMsgCnt(self.regulatorQueueName)
                msg = self._messageAgent.getMsg(self.regulatorQueueName)
                msgType = msg.getMessageType()
                if msgType == None:
                    pass
                else:
                    body = msg.getbody()
                    if self._messageAgent.isCommand(body):
                        self._commandHandler(body)
                    else:
                        self.logger.error("Unknown massage body:{0}".format(body))
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, 
                "Regulator msg handler")
        finally:
            pass

    def retryFailureRequests(self):
        requestTupleList = self._oib.getAllRequest()
        # " REQUEST_UUID, REQUEST_TYPE, SFC_UUID, SFCIID, CMD_UUID, STATE, PICKLE, RETRY_CNT "
        for requestTuple in requestTupleList:
            state = requestTuple[5]
            if state == REQUEST_STATE_FAILED:
                requestUUID = requestTuple[0]
                requestType = requestTuple[1]
                request = requestTuple[6]
                retryCnt = requestTuple[7]
                if retryCnt > MAX_RETRY_NUM:
                    continue
                self._oib.updateRequestState(requestUUID, REQUEST_STATE_IN_PROCESSING)
                self._oib.incRequestRetryCnt(requestUUID)
                if requestType in [REQUEST_TYPE_ADD_SFC, 
                                    REQUEST_TYPE_ADD_SFCI,
                                    REQUEST_TYPE_DEL_SFCI,
                                    REQUEST_TYPE_DEL_SFC]:
                    msg = SAMMessage(MSG_TYPE_REQUEST, request)
                    self._messageAgent.sendMsg(DISPATCHER_QUEUE, msg)
                elif requestType in [REQUEST_TYPE_GET_DCN_INFO]:
                    self.logger.warning("Disable retry for get dcn info request!")
                    # msg = SAMMessage(MSG_TYPE_REQUEST, request)
                    # self._messageAgent.sendMsg(MEASURER_QUEUE, msg)
                else:
                    raise ValueError("Unknown request type {0}".format(requestType))

    def _commandHandler(self, cmd):
        try:
            self.logger.info("Get a command reply")
            cmdID = cmd.cmdID
            if cmd.cmdType == CMD_TYPE_HANDLE_FAILURE_ABNORMAL:
                self.logger.info("Get CMD_TYPE_HANDLE_FAILURE_ABNORMAL!")
                allZoneDetectionDict = cmd.attributes["allZoneDetectionDict"]
                for zoneName, detectionDict in allZoneDetectionDict.items():
                    infSFCIAndSFCUUIDTupleList = self._getInfluencedSFCIAndSFCList(
                                                                zoneName, detectionDict)
                    self.logger.debug("infSFCIAndSFCUUIDTupleList is {0}".format(infSFCIAndSFCUUIDTupleList))
                    for sfci, sfcUUID in infSFCIAndSFCUUIDTupleList:
                        self._sendCmd2Dispatcher(cmd)
                        sfc = self._oib.getSFC4DB(sfcUUID)
                        req = self._genDelSFCIRequest(sfci)
                        self._sendRequest2Dispatcher(req)
                        req = self._genAddSFCIRequest(sfc, sfci)
                        self._sendRequest2Dispatcher(req)
            else:
                pass
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, 
                "Regualtor command handler")
        finally:
            pass

    def _sendCmd2Dispatcher(self, cmd):
        queueName = DISPATCHER_QUEUE
        msg = SAMMessage(MSG_TYPE_REGULATOR_CMD, cmd)
        self._messageAgent.sendMsg(queueName, msg)

    def _getInfluencedSFCIAndSFCList(self, zoneName, detectionDict):
        infSFCIAndSFCUUIDTupleList = []
        sfciTupleList = self.getAllSFCIsFromDB()
        for sfciTuple in sfciTupleList:
            self.logger.info("sfciTuple is {0}".format(sfciTuple))
            sfciZoneName = sfciTuple[6]
            if zoneName == sfciZoneName:
                self.logger.info("Filter influenced sfci.")
                # (SFCIID, SFC_UUID, VNFI_LIST, STATE, PICKLE, ORCHESTRATION_TIME, ZONE_NAME)
                sfcUUID = sfciTuple[1]
                state = sfciTuple[3]
                if not (state == STATE_ACTIVE):
                    continue
                sfci = sfciTuple[4]
                for directionID in [DIRECTION1_PATHID_OFFSET, DIRECTION2_PATHID_OFFSET]:
                    fPathList = []
                    if directionID in sfci.forwardingPathSet.primaryForwardingPath:
                        fPathList.append(sfci.forwardingPathSet.primaryForwardingPath[directionID])
                    if directionID in sfci.forwardingPathSet.backupForwardingPath:
                        fPathList.append(sfci.forwardingPathSet.backupForwardingPath[directionID])
                    for forwardingPath in fPathList:
                        for segPath in forwardingPath:
                            for stage, nodeID in segPath:
                                if self.isNodeIDInDetectionDict(nodeID, detectionDict):
                                    infSFCIAndSFCUUIDTupleList.append((sfci, sfcUUID))
                            for stage, nodeID in segPath[:-2]:
                                linkID = (nodeID, segPath[stage+1])
                                if self.isLinkIDInDetectionDict(linkID, detectionDict):
                                    infSFCIAndSFCUUIDTupleList.append((sfci, sfcUUID))
            else:
                self.logger.debug("zoneName is {0}, sfciZoneName is {1}".format(zoneName, sfciZoneName))
        return infSFCIAndSFCUUIDTupleList

    def isNodeIDInDetectionDict(self, nodeID, detectionDict):
        keyList = ["failure", "abnormal"]
        for key in keyList:
            for listType in ["switchIDList", "serverIDList"]:
                idList = detectionDict[key][listType]
                if nodeID in idList:
                    return True
        return False

    def isLinkIDInDetectionDict(self, linkID, detectionDict):
        keyList = ["failure", "abnormal"]
        for key in keyList:
            for listType in ["linkIDList", "serverIDList"]:
                idList = detectionDict[key][listType]
                if linkID in idList:
                    return True
                reversedLinkID = (linkID[1], linkID[0])
                if reversedLinkID in idList:
                    return True
        return False

    def _genDelSFCIRequest(self, sfci):
        req = Request(0, uuid.uuid1(), REQUEST_TYPE_DEL_SFCI, 
                        attributes={
                            "sfci": sfci
                    })
        return req

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

    def getAllSFCIsFromDB(self):
        sfciTupleList = self._oib.getAllSFCI()
        return sfciTupleList

    def getAllSFCsFromDB(self):
        sfcTupleList = self._oib.getAllSFC()
        return sfcTupleList


if __name__ == "__main__":
    argParser = ArgParser()
    dP = Regulator()
    dP.startRegulator()
