#!/usr/bin/python
# -*- coding: UTF-8 -*-

from functools import wraps
import logging

from sam.base.sfc import STATE_IN_PROCESSING, STATE_ACTIVE, \
    STATE_DELETED, STATE_INACTIVE, STATE_INIT_FAILED, STATE_MANUAL, STATE_UNDELETED
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

    def reConnection(self):
        self.dbA.disconnect()
        self.dbA.connectDB(db = "Orchestrator")

    def reConnectionDecorator(f):
        @wraps(f)
        def decorated(self, *args, **kwargs):
            # if self.dbA.isConnectingDB():
            #     self.dbA.disconnect()
            # self.dbA.connectDB(db = "Orchestrator")
            # f(self, *args, **kwargs)
            # self.dbA.disconnect()

            self.reConnection()
            return f(self, *args, **kwargs)
        return decorated

    def dropTable(self):
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

    @reConnectionDecorator
    def addRequest(self, request, sfcUUID=-1, sfciID=-1, cmdUUID=-1, retryCnt=0):
        if not self.hasRequest(request.requestID):
            fields = " REQUEST_UUID, REQUEST_TYPE, SFC_UUID, SFCIID, CMD_UUID, STATE, PICKLE, RETRY_CNT "
            dataTuple = (
                            request.requestID,
                            request.requestType,
                            sfcUUID, sfciID, cmdUUID,
                            request.requestState,
                            self.pIO.obj2Pickle(request),
                            retryCnt
                        )
            self.dbA.insert("Request", fields, dataTuple)

    @reConnectionDecorator
    def updateRequest(self, request, sfcUUID=None, sfciID=None, cmdUUID=None, retryCnt=None):
        if self.hasRequest(request.requestID):
            fieldsValues = " `REQUEST_TYPE` = ({0}), `STATE` = ({1}), `PICKLE` = ('{2}') ".format(
                                                request.requestType,
                                                request.requestState,
                                                self.pIO.obj2Pickle(request).decode()
                                                )
            if sfcUUID != None:
                fieldsValues += ", `SFC_UUID` = ({0})".format(sfcUUID)
            if sfciID != None:
                fieldsValues += ", `SFCIID` = ({0})".format(sfciID)
            if cmdUUID != None:
                fieldsValues += ", `CMD_UUID` = ({0})".format(cmdUUID)
            if retryCnt != None:
                fieldsValues += ", `RETRY_CNT` = ({0})".format(retryCnt)

            self.dbA.update("`Request`", 
                fieldsValues,
                " `REQUEST_UUID` = ({0}) ".format(
                    request.requestID)
                )

    @reConnectionDecorator
    def hasRequest(self, requestUUID):
        results = self.dbA.query("Request", " REQUEST_UUID ",
                                    " REQUEST_UUID = '{0}'".format(requestUUID))
        if results != ():
            return True
        else:
            return False

    @reConnectionDecorator
    def updateRequestState(self, requestUUID, state):
        if self.hasRequest(requestUUID):
            self.dbA.update("Request", "STATE = {0}".format(state), " REQUEST_UUID = {0}".format(requestUUID))

    @reConnectionDecorator
    def incRequestRetryCnt(self, requestUUID):
        if self.hasRequest(requestUUID):
            retryCnt = self.dbA.query("Request", "RETRY_CNT", " REQUEST_UUID = {0}".format(requestUUID))
            self.dbA.update("Request", "RETRY_CNT = {0}".format(retryCnt+1), " REQUEST_UUID = {0}".format(requestUUID))

    @reConnectionDecorator
    def delRequest(self, requestUUID):
        if self.hasRequest(requestUUID):
            self.dbA.delete("Request", " REQUEST_UUID = '{0}'".format(requestUUID))

    @reConnectionDecorator
    def getAllRequest(self, condition=None):
        fields = " REQUEST_UUID, REQUEST_TYPE, SFC_UUID, SFCIID, CMD_UUID, STATE, PICKLE "
        results = self.dbA.query("Request", fields, condition)
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

    @reConnectionDecorator
    def hasSFC(self, sfcUUID):
        results = self.dbA.query("SFC", " SFC_UUID ",
                                    " SFC_UUID = '{0}'".format(sfcUUID))
        if results != ():
            return True
        else:
            return False

    @reConnectionDecorator
    def delSFC(self, sfcUUID):
        if self.hasSFC(sfcUUID):
            self.dbA.delete("SFC", " SFC_UUID = '{0}'".format(sfcUUID))

    @reConnectionDecorator
    def getAllSFC(self):
        fields = " ZONE_NAME, SFC_UUID, SFCIID_LIST, STATE, PICKLE "
        results = self.dbA.query("SFC", fields)
        sfcTupleList = []
        for sfciTuple in results:
            sfciResList = list(sfciTuple)
            sfciResList[2] = self._decodePickle2Object(sfciResList[2])
            sfciResList[4] = self._decodePickle2Object(sfciResList[4])
            transedSFCITuple = tuple(sfciResList)
            sfcTupleList.append(transedSFCITuple)
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
                    ZONE_NAME VARCHAR(100) NOT NULL,
                    submission_time TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY ( ID )
                    """
                    )

    @reConnectionDecorator
    def addSFCI2DB(self, sfci, sfcUUID, zoneName, state=STATE_IN_PROCESSING, orchTime=-1):
        if not self.hasSFCI(sfci.sfciID):
            fields = " SFCIID, SFC_UUID, VNFI_LIST, STATE, PICKLE, ORCHESTRATION_TIME, ZONE_NAME "
            dataTuple = (
                            sfci.sfciID,
                            sfcUUID,
                            self.pIO.obj2Pickle(sfci.vnfiSequence),
                            state,
                            self.pIO.obj2Pickle(sfci),
                            orchTime,
                            zoneName
                        )
            self.dbA.insert("SFCI", fields, dataTuple)

    @reConnectionDecorator
    def updateSFCI2DB(self, sfci, sfcUUID=None, zoneName=None, state=None, orchTime=None):
        if self.hasSFCI(sfci.sfciID):
            fieldsValues = " `VNFI_LIST` = ('{0}'), `PICKLE` = ('{1}')".format(
                        self.pIO.obj2Pickle(sfci.vnfiSequence).decode(),       
                        self.pIO.obj2Pickle(sfci).decode()
                        )
            if sfcUUID != None:
                fieldsValues += ", `SFC_UUID` = ('{0}')".format(sfcUUID)
            if zoneName != None:
                fieldsValues += ", `ZONE_NAME` = ('{0}')".format(zoneName)
            if state != None:
                fieldsValues += ", `STATE` = ('{0}')".format(state)
            if orchTime != None:
                fieldsValues += ", `ORCHESTRATION_TIME` = ({0})".format(orchTime)

            self.dbA.update("`SFCI`", 
                fieldsValues,
                " `SFCIID` = ({0}) ".format(
                    sfci.sfciID)
                )

    @reConnectionDecorator
    def hasSFCI(self, sfciID):
        results = self.dbA.query("SFCI", " SFCIID ",
                                    " SFCIID = '{0}'".format(sfciID))
        if results != ():
            return True
        else:
            return False

    @reConnectionDecorator
    def delSFCI(self, sfciID):
        if self.hasSFCI(sfciID):
            self.dbA.delete("SFCI", " SFCIID = '{0}'".format(sfciID))

    @reConnectionDecorator
    def getAllSFCI(self):
        fields = " SFCIID, SFC_UUID, VNFI_LIST, STATE, PICKLE, ORCHESTRATION_TIME, ZONE_NAME "
        results = self.dbA.query("SFCI", fields)
        sfciTupleList = []
        for sfciTuple in results:
            sfciResList = list(sfciTuple)
            sfciResList[4] = self._decodePickle2Object(sfciResList[4])
            transedSFCITuple = tuple(sfciResList)
            sfciTupleList.append(transedSFCITuple)
        return sfciTupleList

    @reConnectionDecorator
    def getAllVNFI(self):
        sfciTupleList = self.getAllSFCI()
        totalVNFIList = []
        for sfciTuple in sfciTupleList:
            sfci = self.pIO.pickle2Obj(sfciTuple[-2])
            vnfiList = sfci.vnfiSequence
            totalVNFIList.extend(vnfiList)
            # print("vnfiList:", vnfiList)
        return totalVNFIList

    def _isAddSFCValidState(self, cmd):
        sfc = cmd.attributes['sfc']
        if self.hasSFC(sfc.sfcUUID):
            return False
        else:
            return True

    @reConnectionDecorator
    def addSFCRequestHandler(self, request, cmd):
        request.requestState = REQUEST_STATE_IN_PROCESSING
        self._addRequest2DB(request, cmd)

        sfc = cmd.attributes['sfc']
        self.addSFC2DB(sfc)

    def _isAddSFCIValidState(self, cmd):
        sfci = cmd.attributes['sfci']
        if self.hasSFCI(sfci.sfciID):
            sfciState = self.getSFCIState(sfci.sfciID)
            if sfciState in [STATE_DELETED, STATE_INIT_FAILED]:
                return True
            else:
                return False
        else:
            return True

    @reConnectionDecorator
    def addSFCIRequestHandler(self, request, cmd):
        request.requestState = REQUEST_STATE_IN_PROCESSING

        sfc = cmd.attributes['sfc']
        zoneName = sfc.attributes["zone"]
        sfci = cmd.attributes['sfci']
        if self.hasSFCI(sfci.sfciID):
            sfciState = self.getSFCIState(sfci.sfciID)
            if sfciState in [STATE_DELETED, STATE_INIT_FAILED]:
                self.updateSFCI2DB(sfci, sfc.sfcUUID, zoneName, STATE_IN_PROCESSING)
            else:
                request.requestState = REQUEST_STATE_FAILED
        else:
            self.addSFCI2DB(sfci, sfc.sfcUUID, zoneName)

        self._addRequest2DB(request, cmd)

    def _isDelSFCIValidState(self, cmd):
        sfci = cmd.attributes['sfci']
        if self.hasSFCI(sfci.sfciID):
            sfciState = self.getSFCIState(sfci.sfciID)
            if sfciState in [STATE_INACTIVE, STATE_ACTIVE, STATE_UNDELETED]:
                return True
            else:
                return False
        else:
            return False

    @reConnectionDecorator
    def delSFCIRequestHandler(self, request, cmd):
        request.requestState = REQUEST_STATE_IN_PROCESSING
        self._addRequest2DB(request, cmd)

        sfci = cmd.attributes['sfci']
        sfciID = sfci.sfciID
        self.updateSFCIState(sfciID, STATE_IN_PROCESSING)

    def _isDelSFCValidState(self, cmd):
        sfc = cmd.attributes['sfc']
        if self.hasSFC(sfc.sfcUUID):
            sfcState = self.getSFCState(sfc.sfcUUID)
            sfciIDList = self.getSFCCorrespondingSFCIID4DB(sfc.sfcUUID)
            if sfcState in [STATE_MANUAL]:
                for sfciID in sfciIDList:
                    sfciState = self.getSFCIState(sfciID)
                    if sfciState not in [STATE_DELETED, STATE_INIT_FAILED]:
                        return False
                return True
            else:
                return False
        else:
            return False

    @reConnectionDecorator
    def delSFCRequestHandler(self, request, cmd):
        request.requestState = REQUEST_STATE_IN_PROCESSING
        self._addRequest2DB(request, cmd)

        sfc = cmd.attributes['sfc']
        sfcUUID = sfc.sfcUUID
        self.updateSFCState(sfcUUID, STATE_IN_PROCESSING)

    def cmdRplyHandler(self, request, cmdState):
        (request.requestState, sfcState, sfciState) = \
            self._genRequestSFCAndSFCIState(request, cmdState)

        self.updateRequestState2DB(request, request.requestState)

        sfcUUID = request.attributes['sfc'].sfcUUID
        if request.requestType == REQUEST_TYPE_ADD_SFC or \
            request.requestType == REQUEST_TYPE_DEL_SFC:
            self.updateSFCState(sfcUUID, sfcState)
        elif request.requestType == REQUEST_TYPE_ADD_SFCI:
            sfciID = request.attributes['sfci'].sfciID
            self.updateSFCIState(sfciID, sfciState)
            self._addSFCI2SFCInDB(sfcUUID, sfciID)
        elif request.requestType == REQUEST_TYPE_DEL_SFCI:
            sfciID = request.attributes['sfci'].sfciID
            self.updateSFCIState(sfciID, sfciState)
            # self._delSFCI4SFCInDB(sfcUUID, sfciID)
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
            if request.requestType == REQUEST_TYPE_ADD_SFC:
                sfcState = STATE_INIT_FAILED
                sfciState = None
            elif request.requestType == REQUEST_TYPE_ADD_SFCI:
                sfcState = None
                sfciState = STATE_INIT_FAILED
            elif request.requestType == REQUEST_TYPE_DEL_SFCI:
                sfcState = None
                sfciState = STATE_UNDELETED
            elif request.requestType == REQUEST_TYPE_DEL_SFC:
                sfcState = STATE_UNDELETED
                sfciState = None
            else:
                raise ValueError("Unkown request type.")
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

        if self.hasRequest(request.requestID):
            self.updateRequest(request, sfc.sfcUUID, sfciID, cmd.cmdID)
        else:
            self.addRequest(request, sfc.sfcUUID, sfciID, cmd.cmdID)

    @reConnectionDecorator
    def updateRequestState2DB(self, request, state):
        request.requestState = state
        self.dbA.update("Request", 
            " PICKLE = '{0}' ".format(self._encodeObject2Pickle(request).decode()),
            " REQUEST_UUID = '{0}' ".format(request.requestID)
            )

    @reConnectionDecorator
    def addSFC2DB(self, sfc, sfciIDList=None, state=STATE_IN_PROCESSING):
        if not self.hasSFC(sfc.sfcUUID):
            if sfciIDList == None:
                sfciIDList = []
            fields = " ZONE_NAME, SFC_UUID, SFCIID_LIST, STATE, PICKLE "
            dataTuple = (
                            sfc.attributes["zone"],
                            sfc.sfcUUID,
                            self.pIO.obj2Pickle(sfciIDList),
                            state,
                            self.pIO.obj2Pickle(sfc)
                        )
            self.dbA.insert("SFC", fields, dataTuple)

    @reConnectionDecorator
    def updateSFC2DB(self, sfc, sfciIDList=None, state=STATE_IN_PROCESSING):
        if self.hasSFC(sfc.sfcUUID):
            self.dbA.update("`SFCI`", 
                " `ZONE_NAME` = ({0}), `SFCIID_LIST` = ('{1}')," \
                " `STATE` = ({2}), `PICKLE` = ('{3}') ".format(
                            sfc.attributes["zone"],
                            self.pIO.obj2Pickle(sfciIDList),
                            state,
                            self.pIO.obj2Pickle(sfc)
                ),
                " `SFC_UUID` = ({0}) ".format(
                    sfc.sfcUUID)
                )

    @reConnectionDecorator
    def pruneSFC4DB(self, sfcUUID):
        self.dbA.delete("SFC", " SFC_UUID = '{0}' ".format(sfcUUID))

    @reConnectionDecorator
    def getSFC4DB(self, sfcUUID):
        results = self.dbA.query("SFC", " PICKLE ", 
            " SFC_UUID = '{0}' ".format(sfcUUID))
        if results != ():
            sfc = self._decodePickle2Object(results[0][0])
        else:
            sfc = None
        return sfc

    @reConnectionDecorator
    def getSFCZone4DB(self, sfcUUID):
        results = self.dbA.query("SFC", " ZONE_NAME ", 
            " SFC_UUID = '{0}' ".format(sfcUUID))
        if results != ():
            zoneName = results[0][0]
        else:
            zoneName = None
        return zoneName

    @reConnectionDecorator
    def getSFCCorrespondingSFCIID4DB(self, sfcUUID):
        results = self.dbA.query("SFC", " SFCIID_LIST ", 
            " SFC_UUID = '{0}' ".format(sfcUUID))
        if results != ():
            sfciIDList = self._decodePickle2Object(results[0][0])
        else:
            sfciIDList = []
        return sfciIDList

    @reConnectionDecorator
    def updateSFCState(self, sfcUUID, state):
        self.dbA.update("SFC", " STATE = '{0}' ".format(state),
            " SFC_UUID = '{0}' ".format(sfcUUID))

    @reConnectionDecorator
    def getSFCState(self, sfcUUID):
        results =  self.dbA.query("SFC", " STATE ",
            " SFC_UUID = '{0}' ".format(sfcUUID))
        if results != ():
            state = results[0][0]
        else:
            state = None
        return state

    @reConnectionDecorator
    def _addSFCI2SFCInDB(self, sfcUUID, sfciID):
        results = self.dbA.query("SFC", " SFCIID_LIST ",
            " SFC_UUID = ('{0}') ".format(sfcUUID))
        sfciIDList = self.pIO.pickle2Obj(results[0][0])
        sfciIDList.append(sfciID)
        sfciIDListPickle = self.pIO.obj2Pickle(sfciIDList)
        self.dbA.update("SFC", " SFCIID_LIST = '{0}' ".format(sfciIDListPickle.decode()),
            " SFC_UUID = '{0}' ".format(sfcUUID))

    @reConnectionDecorator
    def _delSFCI4SFCInDB(self, sfcUUID, sfciID):
        results = self.dbA.query("SFC", " SFCIID_LIST ",
            " SFC_UUID = ('{0}') ".format(sfcUUID))
        sfciIDList = self.pIO.pickle2Obj(results[0][0])
        sfciIDList.remove(sfciID)
        sfciIDListPickle = self.pIO.obj2Pickle(sfciIDList)
        self.dbA.update("SFC", " SFCIID_LIST = '{0}' ".format(sfciIDListPickle.decode()),
            " SFC_UUID = '{0}' ".format(sfcUUID))

    @reConnectionDecorator
    def getSFCI4DB(self, sfciID):
        results = self.dbA.query("SFCI", " PICKLE ", " SFCIID = '{0}' ".format(sfciID))
        if results != ():
            sfci = self._decodePickle2Object(results[0][0])
        else:
            sfci = None
        return sfci

    @reConnectionDecorator
    def updateSFCIState(self, sfciID, state):
        self.dbA.update("SFCI", " STATE = '{0}' ".format(state),
            " SFCIID = '{0}'".format(sfciID))

    @reConnectionDecorator
    def getSFCIState(self, sfciID):
        results = self.dbA.query("SFCI", " STATE ", 
            " SFCIID = '{0}' ".format(sfciID))
        if results != ():
            state = results[0][0]
        else:
            state = None
        return state

    @reConnectionDecorator
    def pruneSFCI4DB(self, sfciID):
        self.dbA.delete("SFCI", " SFCIID = '{0}' ".format(sfciID))

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)
