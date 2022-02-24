#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
if sys.version > '3':
    import queue as Queue
else:
    import Queue
import time
import copy

from sam.base.messageAgent import *
from sam.base.request import Request, Reply
from sam.orchestration.argParser import ArgParser
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor
from sam.measurement.dcnInfoBaseMaintainer import *
from sam.orchestration.oDcnInfoRetriever import *
from sam.orchestration.oSFCAdder import *
from sam.orchestration.oSFCDeleter import *
from sam.orchestration.oConfig import *
from sam.orchestration.orchInfoBaseMaintainer import OrchInfoBaseMaintainer


class Orchestrator(object):
    def __init__(self, orchestrationName=None, podNum=None, minPodIdx=None, maxPodIdx=None):
        # time.sleep(15)   # wait for other basic module boot

        logConfigur = LoggerConfigurator(__name__, './log',
            'orchestrator_{0}.log'.format(orchestrationName), level='info')
        self.logger = logConfigur.getLogger()

        self.podNum = podNum
        self.minPodIdx = minPodIdx
        self.maxPodIdx = maxPodIdx

        self._dib = DCNInfoBaseMaintainer()
        self._oib = OrchInfoBaseMaintainer("localhost", "dbAgent", "123")
        self._cm = CommandMaintainer()

        # self._odir = ODCNInfoRetriever(self._dib, self.logger)
        self._osa = OSFCAdder(self._dib, self.logger, podNum, minPodIdx, maxPodIdx)
        self._osd = OSFCDeleter(self._dib, self._oib, self.logger)

        self._messageAgent = MessageAgent(self.logger)
        if orchestrationName == None:
            self.orchInstanceQueueName = ORCHESTRATOR_QUEUE
        else:
            self.orchInstanceQueueName = ORCHESTRATOR_QUEUE + "_{0}".format(orchestrationName)
        self._messageAgent.startRecvMsg(self.orchInstanceQueueName)

        self._requestBatchQueue = Queue.Queue()
        self._batchMode = True
        self._batchSize = BATCH_SIZE
        self.batchTimeout = BATCH_TIMEOUT

        self.runningState = True
        self.recvKillCommand = False

        self.requestCnt = 0

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
                    self._requestHandler(body)
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

    def _requestHandler(self, request):
        try:
            if request.requestType == REQUEST_TYPE_ADD_SFC:
                # self._odir.getDCNInfo()
                cmd = self._osa.genAddSFCCmd(request)
                self._cm.addCmd(cmd)
                self._oib.addSFCRequestHandler(request, cmd)
                self.sendCmd(cmd)
            elif request.requestType == REQUEST_TYPE_ADD_SFCI:
                if self._batchMode == False:
                    raise ValueError("Deprecated function: genAddSFCICmd"
                        "Please use batch mode!")
                    # self._odir.getDCNInfo()
                    # cmd = self._osa.genAddSFCICmd(request)
                    # self._cm.addCmd(cmd)
                    # self._oib.addSFCIRequestHandler(request, cmd)
                    # self.sendCmd(cmd)
                else:
                    self._requestBatchQueue.put(request)
                    self.logger.debug("put req into requestBatchQueue")
                    if self._requestBatchQueue.qsize() >= self._batchSize and self.runningState == True:
                        self.requestCnt += self._requestBatchQueue.qsize()
                        self.logger.warning("{0}'s self.requestCnt: {1}".format(self.orchInstanceQueueName, self.requestCnt))

                        self.logger.info("Trigger batch process.")
                        # self._odir.getDCNInfo()
                        reqCmdTupleList = self._osa.genABatchOfRequestAndAddSFCICmds(
                            self._requestBatchQueue)
                        # self.logger.info("After mapping, there are {0} request in queue".format(self._requestBatchQueue.qsize()))
                        for (request, cmd) in reqCmdTupleList:
                            self._cm.addCmd(cmd)
                            if ENABLE_OIB:
                                self._oib.addSFCIRequestHandler(request, cmd)
                            self.sendCmd(cmd)
                        self.logger.info("Batch process finish")
                        self.batchLastTime = time.time()
            elif request.requestType == REQUEST_TYPE_DEL_SFCI:
                cmd = self._osd.genDelSFCICmd(request)
                self.logger.debug("orchestrator classifier's serverID: {0}".format(
                    cmd.attributes['sfc'].directions[0]['ingress'].getServerID()
                ))
                self._cm.addCmd(cmd)
                self._oib.delSFCIRequestHandler(request, cmd)
                self.sendCmd(cmd)
            elif request.requestType == REQUEST_TYPE_DEL_SFC:
                cmd = self._osd.genDelSFCCmd(request)
                self._cm.addCmd(cmd)
                self._oib.delSFCRequestHandler(request, cmd)
                self.sendCmd(cmd)
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

    def processAllAddSFCIRequests(self):
        self.logger.debug("Batch time out.")
        if self._requestBatchQueue.qsize() > 0 and self.runningState == True:
            self.logger.info("Timeout process - self._requestBatchQueue.qsize():{0}".format(self._requestBatchQueue.qsize()))
            self.requestCnt += self._requestBatchQueue.qsize()
            reqCmdTupleList = self._osa.genABatchOfRequestAndAddSFCICmds(
                self._requestBatchQueue)
            for (request, cmd) in reqCmdTupleList:
                self._cm.addCmd(cmd)
                self._oib.addSFCIRequestHandler(request, cmd)
                self.sendCmd(cmd)
            self.logger.warning("{0}'s self.requestCnt: {1}".format(self.orchInstanceQueueName, self.requestCnt))

    def sendCmd(self, cmd):
        msg = SAMMessage(MSG_TYPE_ORCHESTRATOR_CMD, cmd)
        self._messageAgent.sendMsg(MEDIATOR_QUEUE, msg)

    def _commandReplyHandler(self, cmdRply):
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
            cmdID = cmd.cmdID
            if cmd.cmdType == CMD_TYPE_PUT_ORCHESTRATION_STATE:
                self.logger.info("Get dib from dispatcher!")
                newDib = self._pruneDib(cmd.attributes["dib"])
                self._dib.updateByNewDib(newDib)
                # self._osa.nPInstance.updateServerSets(self.podNum, self.minPodIdx, self.maxPodIdx)
            elif cmd.cmdType == CMD_TYPE_GET_ORCHESTRATION_STATE:
                pass
                # TODO
            elif cmd.cmdType == CMD_TYPE_TURN_ORCHESTRATION_ON:
                self.logger.info("turn on")
                self.runningState = True
            elif cmd.cmdType == CMD_TYPE_TURN_ORCHESTRATION_OFF:
                self.logger.info("turn off")
                self.runningState = False
            elif cmd.cmdType == CMD_TYPE_KILL_ORCHESTRATION:
                self.logger.info("kill orchestrator")
                self.recvKillCommand = True
            else:
                pass
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex, 
                "Orchestrator command handler")
        finally:
            pass

    def _pruneDib(self, dib):
        # For fast orchestration, we need lower down topology scale
        zoneNameList = dib.getAllZone()
        self.logger.warning("zoneNameList: {0}".format(zoneNameList))
        for zoneName in zoneNameList:
            # prune links
            links = dib.getLinksByZone(zoneName)
            for linkID in links.keys():
                srcID = linkID[0]
                dstID = linkID[1]
                for nodeID in linkID:
                    if dib.isServerID(nodeID):
                        switch = dib.getConnectedSwitch(nodeID, zoneName)
                        switchID = switch.switchID
                        if not self.isSwitchInSubTopologyZone(switchID):
                            # self.logger.warning("delink: {0}->{1}".format(srcID, dstID))
                            dib.delLink(srcID, dstID, zoneName)
                            break
                    elif dib.isSwitchID(nodeID):
                        if not self.isSwitchInSubTopologyZone(nodeID):
                            # self.logger.warning("delink: {0}->{1}".format(srcID, dstID))
                            dib.delLink(srcID, dstID, zoneName)
                            break

            # prune servers
            servers = dib.getServersByZone(zoneName)
            for serverID in servers.keys():
                switch = dib.getConnectedSwitch(serverID, zoneName)
                switchID = switch.switchID
                if not self.isSwitchInSubTopologyZone(switchID):
                    # self.logger.warning("deServer: {0}".format(serverID))
                    dib.delServer(serverID, zoneName)

            # prune switches
            switches = dib.getSwitchesByZone(zoneName)
            for switchID in switches.keys():
                if not self.isSwitchInSubTopologyZone(switchID):
                    # self.logger.warning("deSwitch: {0}".format(switchID))
                    dib.delSwitch(switchID, zoneName)

        return dib

    def isSwitchInSubTopologyZone(self, switchID):
        coreSwitchNum = math.pow(self.podNum/2, 2)
        aggSwitchNum = self.podNum * self.podNum / 2
        coreSwitchPerPod = math.floor(coreSwitchNum/self.podNum)
        # get core switch range
        minCoreSwitchIdx = self.minPodIdx * coreSwitchPerPod
        maxCoreSwitchIdx = minCoreSwitchIdx + coreSwitchPerPod * (self.maxPodIdx - self.minPodIdx + 1) - 1
        # get agg switch range
        minAggSwitchIdx = coreSwitchNum + self.minPodIdx * self.podNum / 2
        maxAggSwitchIdx = minAggSwitchIdx + self.podNum / 2 * (self.maxPodIdx - self.minPodIdx + 1) - 1
        # get tor switch range
        minTorSwitchIdx = coreSwitchNum + aggSwitchNum + self.minPodIdx * self.podNum / 2
        maxTorSwitchIdx = minTorSwitchIdx + self.podNum / 2 * (self.maxPodIdx - self.minPodIdx + 1) - 1
        # self.logger.info("{0},{1},{2},{3},{4},{5}".format(
        #         minCoreSwitchIdx, maxCoreSwitchIdx,
        #         minAggSwitchIdx, maxAggSwitchIdx,
        #         minTorSwitchIdx, maxTorSwitchIdx
        #     )
        # )

        if (switchID >= minCoreSwitchIdx and switchID <= maxCoreSwitchIdx) \
                or (switchID >= minAggSwitchIdx and switchID <= maxAggSwitchIdx) \
                or (switchID >= minTorSwitchIdx and switchID <= maxTorSwitchIdx):
            return True
        else:
            return False



if __name__=="__main__":
    argParser = ArgParser()
    name = argParser.getArgs()['name']   # example: 0-35
    podNum = argParser.getArgs()['p']   # example: 36
    minPodIdx = argParser.getArgs()['minPIdx']   # example: 0
    maxPodIdx = argParser.getArgs()['maxPIdx']   # example: 35
    turnOff = argParser.getArgs()['turnOff']

    ot = Orchestrator(name, podNum, minPodIdx, maxPodIdx)
    if turnOff:
        ot.setRunningState(False)
    ot.startOrchestrator()
