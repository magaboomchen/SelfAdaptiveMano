#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
Input: recieve failure/abnormal notification command from inteligent module
Output: send del/add SFCI request to dispatcher

Get SFCI from db, check which switch/server has been used for each SFCI.

"""

import uuid
from sam.base.command import CMD_TYPE_HANDLE_FAILURE_ABNORMAL
from sam.base.path import DIRECTION1_PATHID_OFFSET, DIRECTION2_PATHID_OFFSET
from sam.base.pickleIO import PickleIO
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.messageAgent import DISPATCHER_QUEUE, MSG_TYPE_REQUEST, REGULATOR_QUEUE, \
                                    MessageAgent, SAMMessage
from sam.base.request import REQUEST_TYPE_ADD_SFCI, REQUEST_TYPE_DEL_SFCI, Request
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer
from sam.regulator.argParser import ArgParser


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

    def startRegulator(self):
        self.startRoutine()

    def startRoutine(self):
        try:
            while True:
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

    def _commandHandler(self, cmd):
        try:
            self.logger.info("Get a command reply")
            cmdID = cmd.cmdID
            if cmd.cmdType == CMD_TYPE_HANDLE_FAILURE_ABNORMAL:
                self.logger.info("Get CMD_TYPE_HANDLE_FAILURE_ABNORMAL!")
                infSFCIAndSFCUUIDTupleList = self._getInfluencedSFCIAndSFCList(cmd.attributes["detection"])
                for sfci, sfcUUID in infSFCIAndSFCUUIDTupleList:
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

    def _getInfluencedSFCIAndSFCList(self, detectionDict):
        infSFCIAndSFCUUIDTupleList = []
        sfciTupleList = self.getAllSFCIsFromDB()
        for sfciTuple in sfciTupleList:
            self.logger.info("sfciTuple is {0}".format(sfciTuple))
            # (SFCIID, SFC_UUID, VNFI_LIST, STATE, PICKLE, ORCHESTRATION_TIME)
            sfcUUID = sfciTuple[1]
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
