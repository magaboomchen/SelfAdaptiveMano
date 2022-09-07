#!/usr/bin/python
# -*- coding: UTF-8 -*-

from uuid import UUID
from functools import wraps
from typing import List, Tuple

from sam.base.sfc import SFC, SFCI
from sam.base.sfcConstant import STATE_IN_PROCESSING, STATE_ACTIVE, \
    STATE_DELETED, STATE_INACTIVE, STATE_INIT_FAILED, STATE_MANUAL, \
    STATE_RECOVER_MODE, STATE_UNDELETED
from sam.base.command import CMD_STATE_SUCCESSFUL, CMD_STATE_FAIL, Command
from sam.base.request import REQUEST_TYPE_ADD_SFC, REQUEST_TYPE_ADD_SFCI, \
    REQUEST_TYPE_DEL_SFCI, REQUEST_TYPE_DEL_SFC, REQUEST_STATE_SUCCESSFUL, \
    REQUEST_STATE_FAILED, Request
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
    def addRequest(self, request, sfcUUID=None, sfciID=None, cmdUUID=None, retryCnt=0):
        # type: (Request, UUID, int, UUID, int) -> None
        if not self.hasRequest(request.requestID):
            fields = " REQUEST_UUID, REQUEST_TYPE, STATE, PICKLE"
            dataList = [request.requestID, request.requestType, 
                            request.requestState,
                            self.pIO.obj2Pickle(request)]
            if sfcUUID != None:
                fields += ", SFC_UUID".format(sfcUUID)
                dataList.append(sfcUUID)
            if sfciID != None:
                fields += ", SFCIID".format(sfciID)
                dataList.append(sfciID)
            if cmdUUID != None:
                fields += ", CMD_UUID".format(cmdUUID)
                dataList.append(cmdUUID)
            if retryCnt != None:
                fields += ", RETRY_CNT".format(retryCnt)
                dataList.append(retryCnt)

            dataTuple = tuple(dataList)
            self.dbA.insert("Request", fields, dataTuple)

    @reConnectionDecorator
    def updateRequest(self, request, sfcUUID=None, sfciID=None, cmdUUID=None, retryCnt=None):
        # type: (Request, UUID, int, UUID, int) -> None
        if self.hasRequest(request.requestID):
            fieldsValues = " `REQUEST_TYPE` = ('{0}'), `STATE` = ('{1}'), `PICKLE` = ('{2}') ".format(
                                                request.requestType,
                                                request.requestState,
                                                self.pIO.obj2Pickle(request).decode()
                                                )
            if sfcUUID != None:
                fieldsValues += ", `SFC_UUID` = ('{0}')".format(sfcUUID)
            if sfciID != None:
                fieldsValues += ", `SFCIID` = ({0})".format(sfciID)
            if cmdUUID != None:
                fieldsValues += ", `CMD_UUID` = ('{0}')".format(cmdUUID)
            if retryCnt != None:
                fieldsValues += ", `RETRY_CNT` = ({0})".format(retryCnt)

            self.dbA.update("`Request`", 
                fieldsValues,
                " `REQUEST_UUID` = ('{0}') ".format(
                    request.requestID)
                )

    @reConnectionDecorator
    def hasRequest(self, requestUUID):
        results = self.dbA.query("Request", " REQUEST_UUID ",
                                    " REQUEST_UUID = '{0}' ".format(requestUUID))
        if results != ():
            return True
        else:
            return False

    @reConnectionDecorator
    def incRequestRetryCnt(self, requestUUID):
        if self.hasRequest(requestUUID):
            results = self.dbA.query("Request", " RETRY_CNT ", " REQUEST_UUID = '{0}' ".format(requestUUID))
            print(results)
            retryCnt = results[0][0]
            self.dbA.update("Request", " RETRY_CNT = {0} ".format(retryCnt+1), " REQUEST_UUID = '{0}' ".format(requestUUID))

    @reConnectionDecorator
    def getRequestRetryCnt(self, requestUUID):
        results = self.dbA.query("Request", 
            " RETRY_CNT ", " REQUEST_UUID = '{0}' ".format(requestUUID))
        return results[0][0]

    @reConnectionDecorator
    def delRequest(self, requestUUID):
        if self.hasRequest(requestUUID):
            self.dbA.delete("Request", " REQUEST_UUID = '{0}'".format(requestUUID))

    @reConnectionDecorator
    def getAllRequest(self, condition=None):
        fields = " REQUEST_UUID, REQUEST_TYPE, SFC_UUID, SFCIID, CMD_UUID, STATE, PICKLE, RETRY_CNT "
        results = self.dbA.query("Request", fields, condition)
        requestTupleList = []
        for requestTuple in results: 
            reqResList = list(requestTuple)
            reqResList[-2] = self._decodePickle2Object(reqResList[-2])
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
        # type: (UUID) -> bool
        results = self.dbA.query("SFC", " SFC_UUID ",
                                    " SFC_UUID = '{0}'".format(sfcUUID))
        if results != ():
            return True
        else:
            return False

    @reConnectionDecorator
    def delSFC(self, sfcUUID):
        # type: (UUID) -> None
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
        # type: (SFCI, UUID, str, str, float) -> None
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
        # type: (SFCI, UUID, str, str, float) -> None
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
        # type: (int) -> bool
        results = self.dbA.query("SFCI", " SFCIID ",
                                    " SFCIID = '{0}'".format(sfciID))
        if results != ():
            return True
        else:
            return False

    @reConnectionDecorator
    def delSFCI(self, sfciID):
        # type: (int) -> None
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

    def isAddSFCValidState(self, sfcUUID):
        # type: (Command) -> bool
        if self.hasSFC(sfcUUID):
            sfcState = self.getSFCState(sfcUUID)
            if sfcState in [STATE_DELETED, STATE_INIT_FAILED]:
                return True
            else:
                return False
        else:
            return True

    @reConnectionDecorator
    def addSFCRequestHandler(self, request, cmd, requestState, sfcState):
        # type: (Request, Command, str, str) -> None
        request.requestState = requestState
        self.addCmdInfo2Request(request, cmd)

        sfc = cmd.attributes['sfc']
        self.addSFC2DB(sfc, state=sfcState)

    def isAddSFCIValidState(self, sfciID):
        # type: (SFCI.sfciID) -> bool
        if self.hasSFCI(sfciID):
            sfciState = self.getSFCIState(sfciID)
            if sfciState in [STATE_DELETED, STATE_INIT_FAILED]:
                return True
            else:
                return False
        else:
            return True

    @reConnectionDecorator
    def addSFCIRequestHandler(self, request, cmd, requestState, 
                                sfciState, orchTime):
        # type: (Request, Command, str, str, float) -> None
        request.requestState = requestState

        sfc = cmd.attributes['sfc']
        zoneName = sfc.attributes["zone"]
        sfci = cmd.attributes['sfci']
        if self.hasSFCI(sfci.sfciID):
            sfciState = self.getSFCIState(sfci.sfciID)
            if sfciState in [STATE_DELETED, STATE_INIT_FAILED]:
                self.updateSFCI2DB(sfci, sfc.sfcUUID, zoneName, 
                                    STATE_IN_PROCESSING)
            else:
                request.requestState = REQUEST_STATE_FAILED
        else:
            self.addSFCI2DB(sfci, sfc.sfcUUID, zoneName, orchTime=orchTime)

        self.addCmdInfo2Request(request, cmd)

    def isDelSFCIValidState(self, sfciID):
        # type: (SFCI.sfciID) -> bool
        if self.hasSFCI(sfciID):
            sfciState = self.getSFCIState(sfciID)
            if sfciState in [STATE_INACTIVE, STATE_ACTIVE, STATE_UNDELETED]:
                return True
            else:
                return False
        else:
            return False

    @reConnectionDecorator
    def delSFCIRequestHandler(self, request, cmd, requestState, sfciState):
        # type: (Request, Command, str, str) -> None
        request.requestState = requestState
        self.addCmdInfo2Request(request, cmd)

        sfci = cmd.attributes['sfci']
        sfciID = sfci.sfciID
        self.updateSFCIState(sfciID, sfciState)

    def isDelSFCValidState(self, sfcUUID):
        # type: (UUID) -> bool
        if self.hasSFC(sfcUUID):
            sfcState = self.getSFCState(sfcUUID)
            sfciIDList = self.getSFCIIDListOfASFC4DB(sfcUUID)
            if sfcState in [STATE_MANUAL, STATE_RECOVER_MODE]:
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
    def delSFCRequestHandler(self, request, cmd,
                                requestState, sfcState):
        # type: (Request, Command, str, str) -> None
        request.requestState = requestState
        self.addCmdInfo2Request(request, cmd)

        sfc = cmd.attributes['sfc'] # type: SFC
        sfcUUID = sfc.sfcUUID
        if sfcState == STATE_IN_PROCESSING:
            self.updateSFCState(sfcUUID, sfcState)

    def cmdRplyHandler(self, request, cmdState):
        # type: (Request, str) -> None
        (request.requestState, sfcState, sfciState) = \
            self._genRequestSFCAndSFCIState(request, cmdState)

        self.updateRequestState2DB(request, request.requestState)

        sfcUUID = request.attributes['sfc'].sfcUUID
        if request.requestType == REQUEST_TYPE_ADD_SFC or \
            request.requestType == REQUEST_TYPE_DEL_SFC:
            self.updateSFCState(sfcUUID, sfcState)
        elif request.requestType == REQUEST_TYPE_ADD_SFCI:
            sfciID = request.attributes['sfci'].sfciID
            self._addSFCI2SFCInDB(sfcUUID, sfciID)
            self.updateSFCIState(sfciID, sfciState)
        elif request.requestType == REQUEST_TYPE_DEL_SFCI:
            sfciID = request.attributes['sfci'].sfciID
            self.updateSFCIState(sfciID, sfciState)
            # Don't delete SFCIID from SFC's sfciIDList
            # self._delSFCI4SFCInDB(sfcUUID, sfciID)
        else:
            raise ValueError("Unknown request type ")

    def _genRequestSFCAndSFCIState(self, request, cmdState):
        # type: (Request, str) -> Tuple[str, str, str]
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
        # type: (int) -> Request
        results = self.dbA.query("Request", 
            " PICKLE ", " CMD_UUID = '{0}' ".format(cmdID))
        request = self._decodePickle2Object(results[0][0])
        return request

    def getRequestByRequestUUID(self, requestUUID):
        # type: (UUID) -> Request
        results = self.dbA.query("Request", "PICKLE", 
            " REQUEST_UUID = '{0}' ".format(requestUUID))
        request = self._decodePickle2Object(results[0][0])
        return request

    def _encodeObject2Pickle(self, pObject):
        return PickleIO().obj2Pickle(pObject)

    def _decodePickle2Object(self, pickledStr):
        return PickleIO().pickle2Obj(pickledStr)

    def addCmdInfo2Request(self, request, cmd):
        # type: (Request, Command) -> None
        if request.requestType == REQUEST_TYPE_ADD_SFC or \
                request.requestType == REQUEST_TYPE_DEL_SFC:
            sfc = cmd.attributes['sfc']
            sfciID = None
        elif request.requestType == REQUEST_TYPE_ADD_SFCI or \
                request.requestType == REQUEST_TYPE_DEL_SFCI:
            sfc = cmd.attributes['sfc']
            sfci = cmd.attributes['sfci']
            sfciID = sfci.sfciID
        else:
            raise ValueError("Unkown request type. ")

        if self.hasRequest(request.requestID):
            self.updateRequest(request, sfc.sfcUUID, sfciID, cmd.cmdID)
        else:
            self.addRequest(request, sfc.sfcUUID, sfciID, cmd.cmdID)

    @reConnectionDecorator
    def updateRequestState2DB(self, request, state):
        # type: (Request, str) -> None
        request.requestState = state
        if self.hasRequest(request.requestID):
            self.dbA.update("Request", 
                " PICKLE = '{0}', STATE = '{1}' ".format(
                    self._encodeObject2Pickle(request).decode(),
                    state
                    ),
                " REQUEST_UUID = '{0}' ".format(request.requestID)
                )
        else:
            self.addRequest(request)

    @reConnectionDecorator
    def addSFC2DB(self, sfc, sfciIDList=None, state=STATE_IN_PROCESSING):
        # type: (SFC, List[int], str) -> None
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
        else:
            self.updateSFC2DB(sfc, state=state)

    @reConnectionDecorator
    def updateSFC2DB(self, sfc, sfciIDList=None, state=STATE_IN_PROCESSING):
        # type: (SFC, List[int], str) -> None
        if self.hasSFC(sfc.sfcUUID):
            fieldsValues = " `PICKLE` = ('{0}') ".format(
                                    self.pIO.obj2Pickle(sfc).decode()
                                )

            if sfciIDList != None:
                fieldsValues += ", `SFCIID_LIST` = ('{0}')".format(self.pIO.obj2Pickle(sfciIDList))
            if state != None:
                fieldsValues += ", `STATE` = ('{0}')".format(state)

            self.dbA.update("`SFC`", 
                fieldsValues,
                " `SFC_UUID` = ('{0}') ".format(
                    sfc.sfcUUID)
                )

    @reConnectionDecorator
    def pruneSFC4DB(self, sfcUUID):
        # type: (UUID) -> None
        self.dbA.delete("SFC", " SFC_UUID = '{0}' ".format(sfcUUID))

    @reConnectionDecorator
    def getSFC4DB(self, sfcUUID):
        # type: (UUID) -> SFC
        results = self.dbA.query("SFC", " PICKLE ", 
            " SFC_UUID = '{0}' ".format(sfcUUID))
        if results != ():
            sfc = self._decodePickle2Object(results[0][0])
        else:
            sfc = None
        return sfc

    @reConnectionDecorator
    def getSFCZone4DB(self, sfcUUID):
        # type: (UUID) -> str
        results = self.dbA.query("SFC", " ZONE_NAME ", 
            " SFC_UUID = '{0}' ".format(sfcUUID))
        if results != ():
            zoneName = results[0][0]
        else:
            zoneName = None
        return zoneName

    @reConnectionDecorator
    def getSFCIIDListOfASFC4DB(self, sfcUUID):
        # type: (UUID) -> List[int]
        results = self.dbA.query("SFC", " SFCIID_LIST ", 
            " SFC_UUID = '{0}' ".format(sfcUUID))
        if results != ():
            sfciIDList = self._decodePickle2Object(results[0][0])
        else:
            sfciIDList = []
        return sfciIDList

    @reConnectionDecorator
    def updateSFCState(self, sfcUUID, state):
        # type: (UUID, str) -> None
        self.dbA.update("SFC", " STATE = '{0}' ".format(state),
            " SFC_UUID = '{0}' ".format(sfcUUID))

    @reConnectionDecorator
    def getSFCState(self, sfcUUID):
        # type: (UUID) -> str
        results =  self.dbA.query("SFC", " STATE ",
            " SFC_UUID = '{0}' ".format(sfcUUID))
        if results != ():
            state = results[0][0]
        else:
            state = None
        return state

    @reConnectionDecorator
    def _addSFCI2SFCInDB(self, sfcUUID, sfciID):
        # type: (UUID, int) -> None
        results = self.dbA.query("SFC", " SFCIID_LIST ",
            " SFC_UUID = ('{0}') ".format(sfcUUID))
        sfciIDList = self.pIO.pickle2Obj(results[0][0])
        if sfciID not in sfciIDList:
            sfciIDList.append(sfciID)
            sfciIDListPickle = self.pIO.obj2Pickle(sfciIDList)
            self.dbA.update("SFC", " SFCIID_LIST = '{0}' ".format(sfciIDListPickle.decode()),
                " SFC_UUID = '{0}' ".format(sfcUUID))

    @reConnectionDecorator
    def _delSFCI4SFCInDB(self, sfcUUID, sfciID):
        # type: (UUID, int) -> None
        results = self.dbA.query("SFC", " SFCIID_LIST ",
            " SFC_UUID = ('{0}') ".format(sfcUUID))
        sfciIDList = self.pIO.pickle2Obj(results[0][0])
        if sfciID in sfciIDList:
            sfciIDList.remove(sfciID)
            sfciIDListPickle = self.pIO.obj2Pickle(sfciIDList)
            self.dbA.update("SFC", " SFCIID_LIST = '{0}' ".format(sfciIDListPickle.decode()),
                " SFC_UUID = '{0}' ".format(sfcUUID))

    @reConnectionDecorator
    def getSFCI4DB(self, sfciID):
        # type: (int) -> SFCI
        results = self.dbA.query("SFCI", " PICKLE ", " SFCIID = '{0}' ".format(sfciID))
        if results != ():
            sfci = self._decodePickle2Object(results[0][0])
        else:
            sfci = None
        return sfci

    @reConnectionDecorator
    def updateSFCIState(self, sfciID, state):
        # type: (int, str) -> SFCI
        self.dbA.update("SFCI", " STATE = '{0}' ".format(state),
            " SFCIID = '{0}'".format(sfciID))

    @reConnectionDecorator
    def getSFCIState(self, sfciID):
        # type: (int) -> str
        results = self.dbA.query("SFCI", " STATE ", 
            " SFCIID = '{0}' ".format(sfciID))
        if results != ():
            state = results[0][0]
        else:
            state = None
        return state

    @reConnectionDecorator
    def pruneSFCI4DB(self, sfciID):
        # type: (int) -> None
        self.dbA.delete("SFCI", " SFCIID = '{0}' ".format(sfciID))

    @reConnectionDecorator
    def isAllSFCIDeleted(self, sfcUUID):
        sfciIDList = self.getSFCIIDListOfASFC4DB(sfcUUID)
        for sfciID in sfciIDList:
            sfciState = self.getSFCIState(sfciID)
            if sfciState != STATE_DELETED:
                return False
        return True

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)
