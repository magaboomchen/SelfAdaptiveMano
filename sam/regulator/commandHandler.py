#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid

from sam.base.command import CMD_TYPE_HANDLE_FAILURE_ABNORMAL
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.messageAgent import DISPATCHER_QUEUE, MSG_TYPE_REGULATOR_CMD, MSG_TYPE_REQUEST, SAMMessage
from sam.base.path import DIRECTION1_PATHID_OFFSET, DIRECTION2_PATHID_OFFSET
from sam.base.request import REQUEST_TYPE_ADD_SFCI, REQUEST_TYPE_DEL_SFCI, Request
from sam.base.sfc import STATE_ACTIVE


class CommandHandler(object):
    def __init__(self, logger, msgAgent, oib):
        self.logger = logger
        self._messageAgent = msgAgent
        self._oib = oib

    def handle(self, cmd):
        try:
            self.logger.info("Get a command reply")
            if cmd.cmdType == CMD_TYPE_HANDLE_FAILURE_ABNORMAL:
                self.logger.info("Get CMD_TYPE_HANDLE_FAILURE_ABNORMAL!")
                allZoneDetectionDict = cmd.attributes["allZoneDetectionDict"]
                for zoneName, detectionDict in allZoneDetectionDict.items():
                    infSFCIAndSFCTupleList = self._getInfluencedSFCIAndSFCList(
                                                                zoneName, detectionDict)
                    self.logger.debug("infSFCIAndSFCTupleList is {0}".format(infSFCIAndSFCTupleList))
                    infSFCIAndSFCTupleList = self._sortInfSFCIAndSFCTupleList(infSFCIAndSFCTupleList)
                    for sfci, sfc in infSFCIAndSFCTupleList:
                        self._sendCmd2Dispatcher(cmd)
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
        infSFCIAndSFCTupleList = []
        sfciTupleList = self.getAllSFCIsFromDB()
        for sfciTuple in sfciTupleList:
            self.logger.info("sfciTuple is {0}".format(sfciTuple))
            sfciZoneName = sfciTuple[6]
            if zoneName == sfciZoneName:
                self.logger.info("Filter influenced sfci.")
                # (SFCIID, SFC_UUID, VNFI_LIST, STATE, PICKLE, ORCHESTRATION_TIME, ZONE_NAME)
                sfcUUID = sfciTuple[1]
                sfc = self._oib.getSFC4DB(sfcUUID)
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
                                    infSFCIAndSFCTupleList.append((sfci, sfc))
                            for stage, nodeID in segPath[:-2]:
                                linkID = (nodeID, segPath[stage+1])
                                if self.isLinkIDInDetectionDict(linkID, detectionDict):
                                    infSFCIAndSFCTupleList.append((sfci, sfc))
            else:
                self.logger.debug("zoneName is {0}, sfciZoneName is {1}".format(zoneName, sfciZoneName))
        return infSFCIAndSFCTupleList

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

    def _sortInfSFCIAndSFCTupleList(self, infSFCIAndSFCTupleList):
        infSFCIAndSFCTupleList.sort(reverse=True, key=lambda x:x[1].slo.availability)
        return infSFCIAndSFCTupleList

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