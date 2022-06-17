#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging
import pickle
import base64

from sam.base.sfc import STATE_IN_PROCESSING, STATE_ACTIVE, \
    STATE_DELETED, STATE_INACTIVE
from sam.base.command import CMD_STATE_SUCCESSFUL, CMD_STATE_FAIL
from sam.base.request import REQUEST_STATE_IN_PROCESSING, REQUEST_TYPE_ADD_SFC, \
    REQUEST_TYPE_ADD_SFCI, REQUEST_TYPE_DEL_SFCI, REQUEST_TYPE_DEL_SFC, \
    REQUEST_STATE_SUCCESSFUL, REQUEST_STATE_FAILED
from sam.base.xibMaintainer import XInfoBaseMaintainer
from sam.base.pickleIO import PickleIO


class OrchInfoBaseMaintainer(XInfoBaseMaintainer):
    def __init__(self, host, user, passwd, reInitialTable=False):
        super(OrchInfoBaseMaintainer, self).__init__()
        self.addDatabaseAgent(host, user, passwd)
        self.dbA.connectDB(db = "Orchestrator")
        self.reInitialTable = reInitialTable
        self._initRequestTable()
        self._initSFCTable()
        self._initSFCITable()

    def cleanTable(self):
        if self.dbA.hasTable("Orchestrator", "Request"):
            self.dbA.dropTable("Request")
        if self.dbA.hasTable("Orchestrator", "SFC"):
            self.dbA.dropTable("SFC")
        if self.dbA.hasTable("Orchestrator", "SFCI"):
            self.dbA.dropTable("SFCI")

    def _initRequestTable(self):
        if self.reInitialTable:
            self.dbA.dropTable("Request")
        if not self.dbA.hasTable("Orchestrator", "Request"):
            self.dbA.createTable("Request",
                """
                ID INT UNSIGNED AUTO_INCREMENT,
                REQUEST_UUID VARCHAR(36) NOT NULL,
                REQUEST_TYPE VARCHAR(36) NOT NULL,
                SFC_UUID VARCHAR(36),
                SFCIID SMALLINT,
                CMD_UUID VARCHAR(36),
                STATE TEXT NOT NULL,
                PICKLE BLOB,
                RETRY_CNT SMALLINT,
                submission_time TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY ( ID ),
                INDEX SFC_UUID_INDEX (SFC_UUID(36)),
                INDEX SFCIID_INDEX (SFCIID),
                INDEX CMD_UUID_INDEX (CMD_UUID(36))
                """
                )

    def addRequest(self, request, sfcUUID=-1, sfciID=-1, cmdUUID=-1, retryCnt=0):
        if not self.hasRequest(request.requestID):
            fields = " REQUEST_UUID, REQUEST_TYPE, SFC_UUID, SFCIID, CMD_UUID, STATE, PICKLE, RETRY_CNT "
            condition = "'{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}', '{7}' ".format(request.requestID,
                                                    request.requestType,
                                                    sfcUUID, sfciID, cmdUUID,
                                                    request.requestState,
                                                    self.pIO.obj2Pickle(request),
                                                    retryCnt)
            self.dbA.insert("Request", fields, condition)

    def hasRequest(self, requestUUID):
        results = self.dbA.query("Request", " REQUEST_UUID ",
                                    " REQUEST_UUID = '{0}'".format(requestUUID))
        if results != ():
            return True
        else:
            return False

    def updateRequestState(self, requestUUID, state):
        if self.hasRequest(requestUUID):
            self.dbA.update("Request", "STATE = {0}".format(state), " REQUEST_UUID = {0}".format(requestUUID))

    def incRequestRetryCnt(self, requestUUID):
        if self.hasRequest(requestUUID):
            retryCnt = self.dbA.query("Request", "RETRY_CNT", " REQUEST_UUID = {0}".format(requestUUID))
            self.dbA.update("Request", "RETRY_CNT = {0}".format(retryCnt+1), " REQUEST_UUID = {0}".format(requestUUID))

    def delRequest(self, requestUUID):
        if self.hasRequest(requestUUID):
            self.dbA.delete("Request", " REQUEST_UUID = '{0}'".format(requestUUID))

    def getAllRequest(self):
        fields = " REQUEST_UUID, REQUEST_TYPE, SFC_UUID, SFCIID, CMD_UUID, STATE, PICKLE "
        results = self.dbA.query("Request", fields)
        requestTupleList = []
        for requestTuple in results: 
            reqResList = list(requestTuple)
            reqResList[-1] = self._decodePickle2Object(reqResList[-1])
            transedReqTuple = tuple(reqResList)
            requestTupleList.append(transedReqTuple)
        return requestTupleList

    def _initSFCTable(self):
        if self.reInitialTable:
            self.dbA.dropTable("SFC")
        if not self.dbA.hasTable("Orchestrator", "SFC"):
            self.dbA.createTable("SFC",
                """
                ID INT UNSIGNED AUTO_INCREMENT,
                ZONE_NAME VARCHAR(100) NOT NULL,
                SFC_UUID VARCHAR(36) NOT NULL,
                SFCIID_LIST BLOB,
                STATE TEXT NOT NULL,
                PICKLE BLOB,
                submission_time TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY ( ID )
                """
                )

    def addSFC(self, sfc, sfciIDList=None, state=STATE_IN_PROCESSING):
        if not self.hasSFC(sfc.sfcUUID):
            fields = " ZONE_NAME, SFC_UUID, SFCIID_LIST, STATE, PICKLE "
            condition = "'{0}', '{1}', '{2}', '{3}', '{4}' ".format(sfc.attributes["zone"],
                                                    sfc.sfcUUID,
                                                    self.pIO.obj2Pickle(sfciIDList), state,
                                                    self.pIO.obj2Pickle(sfc))
            self.dbA.insert("SFC", fields, condition)

    def hasSFC(self, sfcUUID):
        results = self.dbA.query("SFC", " SFC_UUID ",
                                    " SFC_UUID = '{0}'".format(sfcUUID))
        if results != ():
            return True
        else:
            return False

    def delSFC(self, sfcUUID):
        if self.hasSFC(sfcUUID):
            self.dbA.delete("SFC", " SFC_UUID = '{0}'".format(sfcUUID))

    def getAllSFC(self):
        fields = " ZONE_NAME, SFC_UUID, SFCIID_LIST, STATE, PICKLE "
        results = self.dbA.query("SFC", fields)
        sfcTupleList = []
        for sfcTuple in results:
            sfcTupleList.append(sfcTuple)
        return sfcTupleList

    def _initSFCITable(self):
        if self.reInitialTable:
            self.dbA.dropTable("SFCI")
        if not self.dbA.hasTable("Orchestrator", "SFCI"):
            self.dbA.createTable("SFCI",
                """
                ID INT UNSIGNED AUTO_INCREMENT,
                SFCIID SMALLINT,
                SFC_UUID VARCHAR(36) NOT NULL,
                VNFI_LIST BLOB,
                STATE TEXT NOT NULL,
                PICKLE BLOB,
                ORCHESTRATION_TIME FLOAT,
                submission_time TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY ( ID )
                """
                )

    def addSFCI(self, sfci, sfcUUID, state=STATE_IN_PROCESSING, orchTime=-1):
        if not self.hasSFCI(sfci.sfciID):
            fields = " SFCIID, SFC_UUID, VNFI_LIST, STATE, PICKLE, ORCHESTRATION_TIME "
            condition = "'{0}', '{1}', '{2}', '{3}', '{4}', '{5}' ".format(sfci.sfciID,
                                                    sfcUUID,
                                                    self.pIO.obj2Pickle(sfci.vnfiSequence),
                                                    state,
                                                    self.pIO.obj2Pickle(sfci),
                                                    orchTime)
            logging.info("{0} -> {1}".format(fields, condition))
            self.dbA.insert("SFCI", fields, condition)

    def hasSFCI(self, sfciID):
        results = self.dbA.query("SFCI", " SFCIID ",
                                    " SFCIID = '{0}'".format(sfciID))
        if results != ():
            return True
        else:
            return False

    def delSFCI(self, sfciID):
        if self.hasSFCI(sfciID):
            self.dbA.delete("SFCI", " SFCIID = '{0}'".format(sfciID))

    def getAllSFCI(self):
        fields = " SFCIID, SFC_UUID, VNFI_LIST, STATE, PICKLE, ORCHESTRATION_TIME "
        results = self.dbA.query("SFCI", fields)
        sfciTupleList = []
        for sfciTuple in results:
            sfciResList = list(sfciTuple)
            sfciResList[4] = self._decodePickle2Object(sfciResList[4])
            transedSFCITuple = tuple(sfciResList)
            sfciTupleList.append(transedSFCITuple)
        return sfciTupleList

    def getAllVNFI(self):
        sfciTupleList = self.getAllSFCI()
        totalVNFIList = []
        for sfciTuple in sfciTupleList:
            sfci = self.pIO.pickle2Obj(sfciTuple[-2])
            vnfiList = sfci.vnfiSequence
            totalVNFIList.extend(vnfiList)
            # print("vnfiList:", vnfiList)
        return totalVNFIList

    def addSFCRequestHandler(self, request, cmd):
        request.requestState = REQUEST_STATE_IN_PROCESSING
        self._addRequest2DB(request, cmd)

        sfc = cmd.attributes['sfc']
        self._addSFC2DB(sfc)

    def addSFCIRequestHandler(self, request, cmd):
        request.requestState = REQUEST_STATE_IN_PROCESSING
        self._addRequest2DB(request, cmd)

        sfci = cmd.attributes['sfci']
        self._addSFCI2DB(sfci)

    def delSFCIRequestHandler(self, request, cmd):
        request.requestState = REQUEST_STATE_IN_PROCESSING
        self._addRequest2DB(request, cmd)

        sfci = cmd.attributes['sfci']
        sfciID = sfci.sfciID
        self._updateSFCIState(sfciID, STATE_IN_PROCESSING)

    def delSFCRequestHandler(self, request, cmd):
        request.requestState = REQUEST_STATE_IN_PROCESSING
        self._addRequest2DB(request, cmd)

        sfc = cmd.attributes['sfc']
        sfcUUID = sfc.sfcUUID
        self._updateSFCState(sfcUUID, STATE_IN_PROCESSING)

    def cmdRplyHandler(self, request, cmdState):
        (request.requestState, sfcState, sfciState) = \
            self._genRequestSFCAndSFCIState(request, cmdState)

        self.updateRequestState2DB(request, request.requestState)

        sfcUUID = request.attributes['sfc'].sfcUUID
        if request.requestType == REQUEST_TYPE_ADD_SFC or \
            request.requestType == REQUEST_TYPE_DEL_SFC:
            self._updateSFCState(sfcUUID, sfcState)
        elif request.requestType == REQUEST_TYPE_ADD_SFCI:
            sfciID = request.attributes['sfci'].sfciID
            self._updateSFCIState(sfciID, sfciState)
            self._addSFCI2SFCInDB(sfcUUID, sfciID)
        elif request.requestType == REQUEST_TYPE_DEL_SFCI:
            sfciID = request.attributes['sfci'].sfciID
            self._updateSFCIState(sfciID, sfciState)
            self._delSFCI4SFCInDB(sfcUUID, sfciID)
        else:
            raise ValueError("Unknown request type ")

    def _genRequestSFCAndSFCIState(self, request, cmdState):
        if cmdState == CMD_STATE_SUCCESSFUL:
            request.requestState = REQUEST_STATE_SUCCESSFUL
            if request.requestType == REQUEST_TYPE_ADD_SFC:
                sfcState = STATE_ACTIVE
                sfciState = None
            elif request.requestType == REQUEST_TYPE_ADD_SFCI:
                sfcState = None
                sfciState = STATE_ACTIVE
            elif request.requestType == REQUEST_TYPE_DEL_SFCI:
                sfcState = None
                sfciState = STATE_DELETED
            elif request.requestType == REQUEST_TYPE_DEL_SFC:
                sfcState = STATE_DELETED
                sfciState = None
            else:
                raise ValueError("Unkown request type.")
        elif cmdState == CMD_STATE_FAIL:
            request.requestState = REQUEST_STATE_FAILED
            sfcState = STATE_INACTIVE
            sfciState = STATE_INACTIVE
        else:
            raise ValueError("Unknown cmd state. ")
        return (request.requestState, sfcState, sfciState)

    def getRequestByCmdID(self, cmdID):
        results = self.dbA.query("Request", 
            " PICKLE ", " CMD_UUID = '{0}' ".format(cmdID))
        request = self._decodePickle2Object(results[0][0])
        return request

    def getRequestByRequestUUID(self, requestUUID):
        results = self.dbA.query("Request", "PICKLE", 
            " REQUEST_UUID = '{0}' ".format(requestUUID))
        request = self._decodePickle2Object(results[0][0])
        return request

    def _encodeObject2Pickle(self, pObject):
        return PickleIO().obj2Pickle(pObject)

    def _decodePickle2Object(self, pickledStr):
        return PickleIO().pickle2Obj(pickledStr)

    def _addRequest2DB(self, request, cmd):
        fields = " REQUEST_UUID, REQUEST_TYPE, CMD_UUID, PICKLE, "
        values = " '{0}', '{1}', '{2}', '{3}', ".format(request.requestID,
            request.requestType, cmd.cmdID, self._encodeObject2Pickle(request))

        if request.requestType == REQUEST_TYPE_ADD_SFC or \
                request.requestType == REQUEST_TYPE_DEL_SFC:
            sfc = cmd.attributes['sfc']
            sfciID = -1
            fields = fields + " SFC_UUID "
            values = values + " '{0}' ".format(sfc.sfcUUID)
        elif request.requestType == REQUEST_TYPE_ADD_SFCI or \
                request.requestType == REQUEST_TYPE_DEL_SFCI:
            sfc = cmd.attributes['sfc']
            sfci = cmd.attributes['sfci']
            sfciID = sfci.sfciID
            fields = fields + " SFCIID "
            values = values + " '{0}' ".format(sfci.sfciID)
        else:
            raise ValueError("Unkown request type. ")

        self.addRequest(request, sfc.sfcUUID, sfciID, cmd.cmdID)
        # self.dbA.insert("Request", fields, values)

    def updateRequestState2DB(self, request, state):
        request.requestState = state
        self.dbA.update("Request", 
            " PICKLE = '{0}' ".format(self._encodeObject2Pickle(request)),
            " REQUEST_UUID = '{0}' ".format(request.requestID)
            )

    def _addSFC2DB(self, sfc):
        # fields = " ZONE_NAME, SFC_UUID, SFCIID_LIST, STATE, PICKLE "
        # self.dbA.insert("SFC", fields,
        #     " '{0}', '{1}', '{2}', '{3}' ".format(
        #         sfc.attributes["zone"],
        #         sfc.sfcUUID, "",
        #     STATE_IN_PROCESSING, self._encodeObject2Pickle(sfc)))
        self.addSFC(sfc)

    def _pruneSFC4DB(self, sfcUUID):
        self.dbA.delete("SFC", " SFC_UUID = '{0}' ".format(sfcUUID))

    def getSFC4DB(self, sfcUUID):
        results = self.dbA.query("SFC", " PICKLE ", 
            " SFC_UUID = '{0}' ".format(sfcUUID))
        if results != ():
            sfc = self._decodePickle2Object(results[0][0])
        else:
            sfc = None
        return sfc

    def _updateSFCState(self, sfcUUID, state):
        self.dbA.update("SFC", " STATE = '{0}' ".format(state),
            " SFC_UUID = '{0}' ".format(sfcUUID))

    def _getSFCState(self, sfcUUID):
        results =  self.dbA.query("SFC", " STATE ",
            " SFC_UUID = '{0}' ".format(sfcUUID))
        if results != ():
            state = results[0][0]
        else:
            state = None
        return state

    def _addSFCI2SFCInDB(self, sfcUUID, sfciID):
        results = self.dbA.query("SFC", " SFCIID_LIST ",
            " SFC_UUID = '{0}' ".format(sfcUUID))
        sfciIDList = results[0][0]
        sfciIDList = sfciIDList + "{0},".format(sfciID)
        self.dbA.update("SFC", " SFCIID_LIST = '{0}' ".format(sfciIDList),
            " SFC_UUID = '{0}' ".format(sfcUUID))

    def _delSFCI4SFCInDB(self, sfcUUID, sfciID):
        results = self.dbA.query("SFC", " SFCIID_LIST ",
            " SFC_UUID = '{0}' ".format(sfcUUID))
        sfciIDList = results[0][0]
        sfciIDList = sfciIDList.replace(str(sfciID)+",", "")
        self.dbA.update("SFC", " SFCIID_LIST = '{0}' ".format(sfciIDList),
            " SFC_UUID = '{0}' ".format(sfcUUID))

    def _addSFCI2DB(self, sfci, sfcUUID):
        # self.dbA.insert("SFCI", " SFCIID, SFC_UUID, STATE, PICKLE ", 
        #     " '{0}', '{1}', '{2}', '{3} ".format(sfci.sfciID, sfcUUID, STATE_IN_PROCESSING, 
        #     self._encodeObject2Pickle(sfci)))
        self.addSFCI(sfci, sfcUUID)

    def getSFCI4DB(self, sfciID):
        results = self.dbA.query("SFCI", " PICKLE ", " SFCIID = '{0}' ".format(sfciID))
        if results != ():
            sfci = self._decodePickle2Object(results[0][0])
        else:
            sfci = None
        return sfci

    def _updateSFCIState(self, sfciID, state):
        self.dbA.update("SFCI", " STATE = '{0}' ".format(state),
            " SFCIID = '{0}'".format(sfciID))

    def _getSFCIState(self, sfciID):
        results = self.dbA.query("SFCI", " STATE ", 
            " SFCIID = '{0}' ".format(sfciID))
        if results != ():
            state = results[0][0]
        else:
            state = None
        return state

    def _pruneSFCI4DB(self, sfciID):
        self.dbA.delete("SFCI", " SFCIID = '{0}' ".format(sfciID))

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)
