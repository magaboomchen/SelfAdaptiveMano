#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
if sys.version > '3':
    import queue as Queue
else:
    import Queue
import time
import math

from sam.base.link import Link
from sam.base.sfc import SFC, SFCI
from sam.base.sfcConstant import STATE_IN_PROCESSING, STATE_INACTIVE, STATE_INIT_FAILED, STATE_UNDELETED
from sam.base.messageAgent import SAMMessage, MessageAgent, \
    MEDIATOR_QUEUE, ORCHESTRATOR_QUEUE, MSG_TYPE_ORCHESTRATOR_CMD
from sam.base.request import REQUEST_STATE_IN_PROCESSING, REQUEST_TYPE_ADD_SFC, REQUEST_TYPE_DEL_SFCI, \
    REQUEST_TYPE_DEL_SFC, REQUEST_STATE_FAILED, Request
from sam.base.command import CMD_TYPE_ORCHESTRATION_UPDATE_EQUIPMENT_STATE, \
    CMD_TYPE_ADD_SFC, CMD_TYPE_ADD_SFCI, \
    CMD_TYPE_PUT_ORCHESTRATION_STATE, CMD_TYPE_GET_ORCHESTRATION_STATE, \
    CMD_TYPE_TURN_ORCHESTRATION_ON, CMD_TYPE_TURN_ORCHESTRATION_OFF, \
    CMD_TYPE_KILL_ORCHESTRATION, CMD_TYPE_DEL_SFC, CMD_TYPE_DEL_SFCI, CommandReply
from sam.base.commandMaintainer import CommandMaintainer
from sam.orchestration.argParser import ArgParser
from sam.base.request import REQUEST_TYPE_ADD_SFCI
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.base.server import Server
from sam.base.switch import Switch
from sam.measurement.dcnInfoBaseMaintainer import DCNInfoBaseMaintainer
from sam.orchestration.oConfig import BATCH_SIZE, BATCH_TIMEOUT, \
                                        DEFAULT_MAPPING_TYPE, ENABLE_OIB
from sam.orchestration.oSFCAdder import OSFCAdder
from sam.orchestration.oSFCDeleter import OSFCDeleter
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer


class Orchestrator(object):
    def __init__(self, orchestrationName=None, podNum=None, minPodIdx=None, 
                        maxPodIdx=None, topoType="fat-tree", zoneName=None):
        logConfigur = LoggerConfigurator(__name__, './log',
            'orchestrator_{0}.log'.format(orchestrationName), level='info')
        self.logger = logConfigur.getLogger()

        self.topoType = topoType
        self.zoneName = zoneName

        self.podNum = podNum
        self.minPodIdx = minPodIdx
        self.maxPodIdx = maxPodIdx

        self._dib = DCNInfoBaseMaintainer()
        self._oib = OrchInfoBaseMaintainer("localhost", "dbAgent",
                                            "123", False)
        self._cm = CommandMaintainer()

        self._osa = OSFCAdder(self._dib, self.logger, podNum, minPodIdx,
                                maxPodIdx, self.topoType, self.zoneName)
        self._osd = OSFCDeleter(self._dib, self._oib, self.logger)

        self._messageAgent = MessageAgent(self.logger)
        if orchestrationName == None:
            self.orchInstanceQueueName = ORCHESTRATOR_QUEUE
        else:
            self.orchInstanceQueueName = ORCHESTRATOR_QUEUE \
                                            + "_{0}".format(orchestrationName)
        self._messageAgent.startRecvMsg(self.orchInstanceQueueName)

        self._requestBatchQueue = Queue.Queue()
        self._batchMode = True
        self._batchSize = BATCH_SIZE
        self.batchTimeout = BATCH_TIMEOUT

        self.runningState = True
        self.recvKillCommand = False

        self.requestCnt = 0
        self.requestWaitingQueue = Queue.Queue()

    def setRunningState(self, runningState):
        self.runningState = runningState

    def startOrchestrator(self):
        self.logger.info("startOrchestrator")
        self.batchLastTime = time.time()
        while True:
            msg = self._messageAgent.getMsg(self.orchInstanceQueueName)
            msgType = msg.getMessageType()
            if msgType == None:
                if self.recvKillCommand:
                    break
            else:
                body = msg.getbody()
                if self._messageAgent.isRequest(body):
                    if self.runningState == True:
                        self._requestHandler(body)
                    else:
                        self.requestWaitingQueue.put(body)
                elif self._messageAgent.isCommandReply(body):
                    self._commandReplyHandler(body)
                elif self._messageAgent.isCommand(body):
                    self._commandHandler(body)
                else:
                    self.logger.error("Unknown massage body:{0}".format(body))
            currentTime = time.time()
            if currentTime - self.batchLastTime > self.batchTimeout:
                # self.logger.debug("self.batchLastTime: {0}, currentTime: {1}".format(self.batchLastTime, currentTime))
                self.processAllAddSFCIRequests()
                self.batchLastTime = time.time()
            self.processAllWaitingRequest()

    def processAllWaitingRequest(self):
        if self.runningState == True:
            while not self.requestWaitingQueue.empty():
                request = self.requestWaitingQueue.get()
                self._requestHandler(request)

    def _requestHandler(self, request):
        # type: (Request) -> None
        try:
            if request.requestType == REQUEST_TYPE_ADD_SFC:
                cmd = self._osa.genAddSFCCmd(request)
                sfc = cmd.attributes['sfc'] # type: SFC
                sfcUUID = sfc.sfcUUID
                if self._oib.isAddSFCValidState(sfcUUID):
                    # self._odir.getDCNInfo()
                    cmd.attributes['source'] = self.orchInstanceQueueName
                    self._cm.addCmd(cmd)
                    self.sendCmd(cmd)
                    reqState = REQUEST_STATE_IN_PROCESSING
                    sfcState = STATE_IN_PROCESSING
                else:
                    self.logger.warning("Invalid add SFC state")
                    reqState = REQUEST_STATE_FAILED
                    sfcState = STATE_INIT_FAILED
                if ENABLE_OIB:
                    self._oib.addSFCRequestHandler(request, cmd, reqState, sfcState)
            elif request.requestType == REQUEST_TYPE_ADD_SFCI:
                if self._batchMode == False:
                    raise ValueError("Deprecated function: genAddSFCICmd"
                        "Please use batch mode!")
                else:
                    self._requestBatchQueue.put(request)
                    self.logger.debug("put req into requestBatchQueue")
                    if (self._requestBatchQueue.qsize() >= self._batchSize \
                                            and self.runningState == True):
                        self.processAllAddSFCIRequests()
            elif request.requestType == REQUEST_TYPE_DEL_SFCI:
                cmd = self._osd.genDelSFCICmd(request)
                sfci = cmd.attributes['sfci']
                if self._oib.isDelSFCIValidState(sfci.sfciID):
                    cmd.attributes['source'] = self.orchInstanceQueueName
                    ingress = cmd.attributes['sfc'].directions[0]['ingress']
                    if type(ingress) == Server:
                        self.logger.debug("orchestrator classifier's serverID: {0}".format(
                            ingress.getServerID()
                        ))
                    elif type(ingress) == Switch:
                        self.logger.debug("orchestrator classifier's switchID: {0}".format(
                            ingress.switchID
                        ))
                    self._cm.addCmd(cmd)
                    self.sendCmd(cmd)
                    reqState = REQUEST_STATE_IN_PROCESSING
                    sfciState = STATE_IN_PROCESSING
                else:
                    self.logger.warning("Invalid del SFCI state")
                    reqState = REQUEST_STATE_FAILED
                    sfciState = STATE_UNDELETED
                if ENABLE_OIB:
                    self._oib.delSFCIRequestHandler(request, cmd, reqState, sfciState)
            elif request.requestType == REQUEST_TYPE_DEL_SFC:
                cmd = self._osd.genDelSFCCmd(request)
                sfc = cmd.attributes['sfc']
                if self._oib.isDelSFCValidState(sfc.sfcUUID):
                    cmd.attributes['source'] = self.orchInstanceQueueName
                    self._cm.addCmd(cmd)
                    self.sendCmd(cmd)
                    reqState = REQUEST_STATE_IN_PROCESSING
                    sfcState = STATE_IN_PROCESSING
                else:
                    self.logger.warning("Invalid del SFC state")
                    reqState = REQUEST_STATE_FAILED
                    sfcState = STATE_UNDELETED
                if ENABLE_OIB:
                    self._oib.delSFCRequestHandler(request, cmd, reqState, sfcState)
            else:
                self.logger.warning(
                    "Unknown request:{0}".format(request.requestType)
                    )
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                "orchestrator _requestHandler")
            self._oib.updateRequestState2DB(request, REQUEST_STATE_FAILED)
        finally:
            pass

    def processInvalidAddSFCIRequests(self, requestBatchQueue):
        # type: (Queue.Queue) -> None
        self._validRequestBatchQueue = Queue.Queue()
        self._invalidRequestBatchQueue = Queue.Queue()
        while not requestBatchQueue.empty():
            request = requestBatchQueue.get()   # type: Request
            if self._isValidAddSFCIRequest(request):
                self._validRequestBatchQueue.put(request)
            else:
                self._invalidRequestBatchQueue.put(request)
                request.requestState = REQUEST_STATE_FAILED
                self._oib.addRequest(request)
        self._requestBatchQueue = self._validRequestBatchQueue

    def _isValidAddSFCIRequest(self, request):
        # type: (Request) -> bool
        try:
            assert 'sfc' in request.attributes
            sfc = request.attributes['sfc'] # type: SFC
            assert type(sfc) == SFC
            for direction in sfc.directions:
                self.logger.info("ingress is {0}, egress is {1}".format(
                    direction["ingress"], 
                    direction["egress"]))
                assert direction["ingress"] != None
                assert direction["egress"] != None
            assert 'sfci' in request.attributes
            sfci = request.attributes['sfci'] # type: SFCI
            assert type(sfci) == SFCI
        except Exception as ex:
            return False
        return True

    def processAllAddSFCIRequests(self):
        self.logger.debug("Batch time out.")
        if self._requestBatchQueue.qsize() > 0 and self.runningState == True:
            self.logger.info("Timeout process - self._requestBatchQueue.qsize():{0}".format(self._requestBatchQueue.qsize()))
            self.requestCnt += self._requestBatchQueue.qsize()
            self.logger.warning("{0}'s self.requestCnt: {1}".format(self.orchInstanceQueueName, self.requestCnt))
            self.logger.info("Trigger batch process.")
            self.processInvalidAddSFCIRequests(self._requestBatchQueue)
            reqCmdTupleList = self._osa.genABatchOfRequestAndAddSFCICmds(
                                                self._requestBatchQueue)
            self.logger.info("After mapping, there are {0} request in queue".format(self._requestBatchQueue.qsize()))
            for (request, cmd) in reqCmdTupleList:
                sfci = cmd.attributes['sfci']   # type: SFCI
                sfciID = sfci.sfciID
                if self._oib.isAddSFCIValidState(sfciID):
                    cmd.attributes['source'] = self.orchInstanceQueueName
                    self._cm.addCmd(cmd)
                    self.sendCmd(cmd)
                    reqState = REQUEST_STATE_IN_PROCESSING
                    sfciState = STATE_IN_PROCESSING
                else:
                    self.logger.warning("Invalid add SFCI state")
                    reqState = REQUEST_STATE_FAILED
                    sfciState = STATE_INIT_FAILED
                if ENABLE_OIB:
                    self.logger.info("sfciID is {0}".format(sfciID))
                    self._oib.addSFCIRequestHandler(request, cmd, reqState, sfciState)
            self.logger.warning("{0}'s self.requestCnt: {1}".format(self.orchInstanceQueueName, self.requestCnt))
            self.logger.info("Batch process finish")
            self.batchLastTime = time.time()

    def sendCmd(self, cmd):
        msg = SAMMessage(MSG_TYPE_ORCHESTRATOR_CMD, cmd)
        self._messageAgent.sendMsg(MEDIATOR_QUEUE, msg)

    def _commandReplyHandler(self, cmdRply):
        # type: (CommandReply) -> None
        try:
            self.logger.info("Get a command reply")
            # update cmd state
            cmdID = cmdRply.cmdID
            state = cmdRply.cmdState
            if not self._cm.hasCmd(cmdID):
                self.logger.error(
                    "Unknown command reply, cmdID:{0}".format(cmdID)
                    )
                return 
            self._cm.changeCmdState(cmdID, state)
            self._cm.addCmdRply(cmdID, cmdRply)
            cmdType = self._cm.getCmdType(cmdID)
            self.logger.info("Command:{0}, cmdType:{1}, state:{2}".format(
                cmdID, cmdType, state))

            # find the request by sfcUUID in cmd
            cmd = self._cm.getCmd(cmdID)
            cmdType = self._cm.getCmdType(cmdID)
            if cmdType == CMD_TYPE_ADD_SFC or cmdType == CMD_TYPE_DEL_SFC:
                request = self._oib.getRequestByCmdID(cmd.cmdID)
            elif cmdType == CMD_TYPE_ADD_SFCI or cmdType == CMD_TYPE_DEL_SFCI:
                request = self._oib.getRequestByCmdID(cmd.cmdID)
            else:
                raise ValueError("Unkonw cmd type: {0}".format(cmdType))

            # update request state
            self._oib.cmdRplyHandler(request, state)
            self._cm.delCmdwithChildCmd(cmdID)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, 
                "Orchestrator commandReply handler")
        finally:
            pass

    def _commandHandler(self, cmd):
        try:
            self.logger.info("Get a command reply")
            if cmd.cmdType == CMD_TYPE_PUT_ORCHESTRATION_STATE:
                self.logger.info("Get dib from dispatcher!")
                newDib = self._pruneDib(cmd.attributes["dib"])
                self._dib.updateByNewDib(newDib)
                if DEFAULT_MAPPING_TYPE == "MAPPING_TYPE_NETPACK":
                    self._osa.initNetPack()
                # self._osa.nPInstance.updateServerSets(self.podNum, self.minPodIdx, self.maxPodIdx)
            elif cmd.cmdType == CMD_TYPE_GET_ORCHESTRATION_STATE:
                raise ValueError("Unimplemented cmd type handler CMD_TYPE_GET_ORCHESTRATION_STATE")
            elif cmd.cmdType == CMD_TYPE_TURN_ORCHESTRATION_ON:
                self.logger.info("turn on")
                self.runningState = True
            elif cmd.cmdType == CMD_TYPE_TURN_ORCHESTRATION_OFF:
                self.logger.info("turn off")
                self.runningState = False
            elif cmd.cmdType == CMD_TYPE_KILL_ORCHESTRATION:
                self.logger.info("kill orchestrator")
                self.recvKillCommand = True
            elif cmd.cmdType == CMD_TYPE_ORCHESTRATION_UPDATE_EQUIPMENT_STATE:
                self.logger.info("update equipment state")
                detectionDict = cmd.attributes["detectionDict"]
                self._updateEquipmentState(detectionDict)
            else:
                pass
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, 
                "Orchestrator command handler")
        finally:
            pass

    def _pruneDib(self, dib):
        # For fast orchestration, we need lower down topology scale
        # zoneNameList = dib.getAllZone()
        # self.logger.info("zoneNameList: {0}".format(zoneNameList))
        self._prepareSubZoneSwitchesIdxInfo()
        # for zoneName in zoneNameList:
        # prune links and save servers to delete in a list

        delServerCandidateDict = {}
        delSwitchCandidateDict = {}
        delLinkCandidateDict = {}
        linksInfo = dib.getLinksByZone(self.zoneName)
        for linkID in linksInfo.keys():
            srcID = linkID[0]
            dstID = linkID[1]
            link = linksInfo[linkID]['link']
            for idx, nodeID in enumerate(linkID):
                if dib.isServerID(nodeID):
                    switchID = linkID[1-idx]
                    if dib.isSwitchID(switchID):
                        if not self.isSwitchInSubTopologyZone(switchID):
                            serverID = nodeID
                            delServerCandidateDict[serverID] = 1
                            delSwitchCandidateDict[switchID] = 1
                            # self.logger.warning("delink: {0}->{1}".format(srcID, dstID))
                            delLinkCandidateDict[linkID] = 1
                            # dib.delLink(link, self.zoneName)
                        break
                elif dib.isSwitchID(nodeID):
                    if not self.isSwitchInSubTopologyZone(nodeID):
                        # self.logger.warning("delink: {0}->{1}".format(srcID, dstID))
                        delSwitchCandidateDict[nodeID] = 1
                        delLinkCandidateDict[linkID] = 1
                        # dib.delLink(link, self.zoneName)
                        break

        # prune servers
        for serverID in delServerCandidateDict.keys():
            dib.delServer(serverID, self.zoneName)

        # prune switches
        for switchID in delSwitchCandidateDict.keys():
            dib.delSwitch(switchID, self.zoneName)

        # prune links
        for linkID in delLinkCandidateDict.keys():
            link = Link(linkID[0], linkID[1])
            dib.delLink(link, self.zoneName)

        return dib

    def _prepareSubZoneSwitchesIdxInfo(self):
        if self.topoType == "fat-tree":
            coreSwitchNum = math.pow(self.podNum/2, 2)
            aggSwitchNum = self.podNum * self.podNum / 2
            coreSwitchPerPod = math.floor(coreSwitchNum/self.podNum)
            # get core switch range
            self.minCoreSwitchIdx = self.minPodIdx * coreSwitchPerPod
            self.maxCoreSwitchIdx = self.minCoreSwitchIdx + coreSwitchPerPod * (self.maxPodIdx - self.minPodIdx + 1) - 1
            # get agg switch range
            self.minAggSwitchIdx = coreSwitchNum + self.minPodIdx * self.podNum / 2
            self.maxAggSwitchIdx = self.minAggSwitchIdx + self.podNum / 2 * (self.maxPodIdx - self.minPodIdx + 1) - 1
            # get tor switch range
            self.minTorSwitchIdx = coreSwitchNum + aggSwitchNum + self.minPodIdx * self.podNum / 2
            self.maxTorSwitchIdx = self.minTorSwitchIdx + self.podNum / 2 * (self.maxPodIdx - self.minPodIdx + 1) - 1
        elif self.topoType == "testbed_sw1":
            return True
        else:
            raise ValueError("Unimplementation topo type")

    def isSwitchInSubTopologyZone(self, switchID):
        if self.topoType == "fat-tree":
            if (switchID >= self.minCoreSwitchIdx and switchID <= self.maxCoreSwitchIdx) \
                    or (switchID >= self.minAggSwitchIdx and switchID <= self.maxAggSwitchIdx) \
                    or (switchID >= self.minTorSwitchIdx and switchID <= self.maxTorSwitchIdx):
                return True
            else:
                return False
        elif self.topoType == "testbed_sw1":
            return True
        else:
            raise ValueError("Unimplementation topo type")

    def _updateEquipmentState(self, detectionDict):
        for caseType, equipmentDict in detectionDict.items():
            switchIDList = equipmentDict["switchIDList"]
            for switchID in switchIDList:
                if self._dib.hasSwitch(switchID, self.zoneName):
                    self._dib.updateSwitchState(switchID, self.zoneName, state = STATE_INACTIVE)

            serverIDList = equipmentDict["serverIDList"]
            for serverID in serverIDList:
                if self._dib.hasServer(serverID, self.zoneName):
                    self._dib.updateServerState(serverID, self.zoneName, state = STATE_INACTIVE)

            linkIDList = equipmentDict["linkIDList"]
            for linkID in linkIDList:
                if self._dib.hasLink(linkID[0], linkID[1], self.zoneName):
                    self._dib.updateLinkState(linkID, self.zoneName, state = STATE_INACTIVE)


if __name__=="__main__":
    argParser = ArgParser()
    name = argParser.getArgs()['name']   # example: 0-35
    podNum = argParser.getArgs()['p']   # example: 36
    minPodIdx = argParser.getArgs()['minPIdx']   # example: 0
    maxPodIdx = argParser.getArgs()['maxPIdx']   # example: 35
    turnOff = argParser.getArgs()['turnOff']
    topoType = argParser.getArgs()['topoType']
    zoneName = argParser.getArgs()['zoneName']

    ot = Orchestrator(name, podNum, minPodIdx, maxPodIdx, topoType, zoneName)
    if turnOff:
        ot.setRunningState(False)
    ot.startOrchestrator()
