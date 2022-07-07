#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid
import time
import copy
import base64
if sys.version > '3':
    import _pickle as cPickle
else:
    import cPickle

from sam.base.messageAgent import MessageAgent, SAMMessage, MEDIATOR_QUEUE, \
    MSG_TYPE_REQUEST, SIMULATOR_ZONE
from sam.base.command import CMD_TYPE_ADD_SFCI
from sam.dispatcher.argParser import ArgParser
from sam.dispatcher.dispatcher import Dispatcher


class DispatcherComponentTester(Dispatcher):
    def __init__(self, podNum, parallelMode=True, baseSFCNum=100, topoType="fat-tree"):
        super(DispatcherComponentTester, self).__init__(podNum, parallelMode, topoType)

        self.mediatorQueueName = MEDIATOR_QUEUE
        self._mediatorStubMsgAgent = MessageAgent(self.logger)
        self._mediatorStubMsgAgent.startRecvMsg(self.mediatorQueueName)

        self._testStartTime = None
        self._testEndTime = None
        self.resourceRecordTimeout = 2

        self.baseSFCNum = baseSFCNum
        self.logger.info("baseSFCNum is {0}".format(self.baseSFCNum))

    def processLocalRequests(self, instanceFilePath, enlargeTimes, expNum, mappingType, intrinsicTimeModel):
        self.localRequestMode = True
        self.expNum = expNum
        self.mappingType = mappingType
        self.intrinsicTimeModel = intrinsicTimeModel
        self.sfcLength = self.__parseSFCLength(instanceFilePath)
        self.enlargeTimes = enlargeTimes
        self._init4LocalRequests(instanceFilePath)
        self._testStartTime = time.time()
        self.startLocalRequestsRoutine()
        self.oMDict[SIMULATOR_ZONE].killAllOrchestratorInstances()

    def __parseSFCLength(self, instanceFilePath: str):
        idx1 = instanceFilePath.find("sfcLength=")
        idx2 = instanceFilePath.find(".instance")
        if idx1 != -1 and idx2 != -1:
            sfcLength = int(instanceFilePath[idx1+len("sfcLength="):idx2])
        else:
            sfcLength = 7
        return sfcLength

    def test_parseSFCLength(self):
        filePath = "../instance/instance/fat-tree/0/fat-tree-k=22_V=11.sfcr_set_M=1000.sfcLength=5.instance"
        print(self.__parseSFCLength(filePath))

    def _init4LocalRequests(self, instanceFilePath):
        self._loadInstance(instanceFilePath)
        self._enlargeRequests()
        self._updateRequestToMsgQueue()
        self.oMDict[SIMULATOR_ZONE]._updateDib(self.topologyDict, SIMULATOR_ZONE)
        # decide the orchestrator number and corresponding idx;
        if self.topoType == "fat-tree":
            maxPodNumPerOrchstratorInstance = self.oMDict[SIMULATOR_ZONE]._computeOrchestratorInstanceMaxPodNum(
                            len(self.addSFCIRequests) * (self.enlargeTimes-1))
            maxOrchNum = self.oMDict[SIMULATOR_ZONE]._computeOrchestratorInstanceMaxOrchNum(
                            len(self.addSFCIRequests) * (self.enlargeTimes-1))
            # init X orchestrator instances
            oInfoList = self.oMDict[SIMULATOR_ZONE]._computeOrchInstanceInfoList(maxPodNumPerOrchstratorInstance, maxOrchNum)
            # self.logger.debug("oInfoList:{0}".format(oInfoList))
        elif self.topoType == "testbed_sw1":
            oInfoList = [
                {
                    "name": "{0}_{1}".format(0, 0),
                    "minPodIdx": 0,
                    "maxPodIdx": 0
                }
            ]
        else:
            raise ValueError("Unimplementation of topo type {0}".format(self.topoType))

        for idx,oInfoDict in enumerate(oInfoList):
            # we need turn off orchestrator at initial to put state into it
            oPid = self.oMDict[SIMULATOR_ZONE].initNewOrchestratorInstance(idx, oInfoDict)
            self.oMDict[SIMULATOR_ZONE].addOrchInstance(oInfoDict["name"], oPid, oInfoDict)
            # TODO: put dib into new orchestrator instance
            self.oMDict[SIMULATOR_ZONE].putState2Orchestrator(oInfoDict["name"])
            self.oMDict[SIMULATOR_ZONE].turnOnOrchestrator(oInfoDict["name"])
        self.oMDict[SIMULATOR_ZONE].assignSFC2OrchInstance(self.addSFCIRequests)
        self.__dispatchInitialAddSFCIRequestToOrch()

    def _loadInstance(self, instanceFilePath):
        self.instance = self.pIO.readPickleFile(instanceFilePath)
        self.topologyDict = self.instance['topologyDict']
        self.addSFCIRequests = self.instance['addSFCIRequests']
        self.addSFCIRequests = self.addSFCIRequests[:self.baseSFCNum]

    def _enlargeRequests(self):
        tmpAddSFCIRequests = []
        for idx in range(self.enlargeTimes):
            for req in self.addSFCIRequests:
                tmpReq = copy.deepcopy(req)
                tmpReq.requestID = uuid.uuid1()
                tmpReq.attributes["sfci"].sfciID += idx * len(self.addSFCIRequests)
                tmpAddSFCIRequests.append(tmpReq)
        self.enlargedAddSFCIRequests= tmpAddSFCIRequests

    def _updateRequestToMsgQueue(self):
        for req in self.enlargedAddSFCIRequests:
            msg = SAMMessage(MSG_TYPE_REQUEST, req)
            encodedMsg = self.__encodeMessage(msg)
            self._messageAgent.msgQueues[self.dispatcherQueueName].put(encodedMsg)

    def __encodeMessage(self,message):
        return base64.b64encode(cPickle.dumps(message,-1))

    def __dispatchInitialAddSFCIRequestToOrch(self):
        cnt = 0
        while True:
            if cnt >= len(self.addSFCIRequests):
                break
            msgCnt = self._messageAgent.getMsgCnt(self.dispatcherQueueName)
            if self.autoScale:
                self.oMDict[SIMULATOR_ZONE].scalingOrchestratorInstances(msgCnt)
            msg = self._messageAgent.getMsg(self.dispatcherQueueName)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            else:
                body = msg.getbody()
                if self._messageAgent.isRequest(body):
                    self._requestHandler(body)
                    cnt += 1

        # absorb all initial addSFCCmd
        cnt = 0
        while True:
            msg = self._mediatorStubMsgAgent.getMsg(self.mediatorQueueName)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            else:
                body = msg.getbody()
                if self._messageAgent.isRequest(body):
                    pass
                elif self._messageAgent.isCommandReply(body):
                    pass
                elif self._messageAgent.isCommand(body):
                    cmd = body
                    if cmd.cmdType == CMD_TYPE_ADD_SFCI:
                        cnt += 1
                        self.logger.info("cnt:{0}".format(cnt))
                        if cnt >= len(self.addSFCIRequests):
                            break
                else:
                    self.logger.error("Unknown massage body:{0}".format(body))
        self.logger.info("Absorb all addSFCI commands from mediatorStub.")

    def startLocalRequestsRoutine(self):
        self.logger.info("Dispatch all addSFCIRequests")
        cnt = 0
        self.oMDict[SIMULATOR_ZONE]._recordOrchUtilization()
        lastTime = time.time()
        while True:
            msgCnt = self._messageAgent.getMsgCnt(self.dispatcherQueueName)
            if msgCnt == 0:
                break
            msg = self._messageAgent.getMsg(self.dispatcherQueueName)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            else:
                body = msg.getbody()
                if self._messageAgent.isRequest(body):
                    cnt += 1
                    self._requestHandler(body)
                    self.logger.info("dispatch cnt: {0}".format(cnt))
                elif self._messageAgent.isCommandReply(body):
                    pass
                elif self._messageAgent.isCommand(body):
                    pass
                else:
                    self.logger.error("Unknown massage body:{0}".format(body))
            currentTime = time.time()
            if currentTime - lastTime  > self.resourceRecordTimeout:
                self.oMDict[SIMULATOR_ZONE]._recordOrchUtilization()
                lastTime = time.time()

        # start mediatorStub and recieve all commands, count the commands number, then record the time as orchestration time.
        self.logger.info("Start mediator stub")
        cnt = 0
        lastTime = time.time()
        while True:
            msg = self._mediatorStubMsgAgent.getMsg(self.mediatorQueueName)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
            else:
                body = msg.getbody()
                if self._messageAgent.isRequest(body):
                    pass
                elif self._messageAgent.isCommandReply(body):
                    pass
                elif self._messageAgent.isCommand(body):
                    cmd = body
                    if cmd.cmdType == CMD_TYPE_ADD_SFCI:
                        cnt += 1
                        self.logger.info("recv cmd to mediatorStub, cnt:{0}".format(cnt))
                        self.logger.debug("len(self.enlargedAddSFCIRequests):{0}".format(len(self.enlargedAddSFCIRequests)))
                        self.logger.debug("len(self.addSFCIRequests):{0}".format(len(self.addSFCIRequests)))
                        if ((cnt % self.baseSFCNum) == 0) and self.localRequestMode:
                            self._testEndTime = time.time()
                            totalOrchTime = self._testEndTime - self._testStartTime
                            res = {
                                "totalOrchTime": totalOrchTime,
                                "orchestratorDict": self.oMDict[SIMULATOR_ZONE].getOrchestratorDict()
                            }
                            self.logger.info("totalOrchTime is {0}".format(totalOrchTime))
                            self.logger.info("orchDict is {0}".format(self.oMDict[SIMULATOR_ZONE].getOrchestratorDict()))
                            if self.intrinsicTimeModel:
                                self.pIO.writePickleFile("./res/{0}/{1}/podNum={2}_enlargeTimes={3}_intrinsic.pickle".format(
                                        self.topoType, self.expNum, self.podNum, self.enlargeTimes), res)
                            else:
                                self.pIO.writePickleFile("./res/{0}/{1}/{2}_parallelMode={3}_sfcLength={4}_enlargeTime={5}_cnt={6}_mapType={7}.pickle".format(
                                        self.topoType, self.expNum, self.podNum, int(self.parallelMode), self.sfcLength, self.enlargeTimes, cnt, self.mappingType), res)
                            if cnt >= len(self.enlargedAddSFCIRequests) - len(self.addSFCIRequests):
                                break
                else:
                    self.logger.error("Unknown massage body:{0}".format(body))
            currentTime = time.time()
            if currentTime - lastTime > self.resourceRecordTimeout:
                self.oMDict[SIMULATOR_ZONE]._recordOrchUtilization()
                lastTime = time.time()
            # else:
            #     self.logger.info("time gap: {0}".format(lastTime - currentTime))


if __name__ == "__main__":
    argParser = ArgParser()
    problemInstanceFilePath = argParser.getArgs()['pFilePath']
    podNum = argParser.getArgs()['p']   # example: 36
    enlargeTimes = argParser.getArgs()['et']
    parallelMode = argParser.getArgs()['parallelMode']
    expNum = argParser.getArgs()['expNum']
    mappingType = argParser.getArgs()['mappingType']
    baseSFCNum = argParser.getArgs()['baseSFCNum']
    topoType = argParser.getArgs()['topoType']
    intrinsicTimeModel = argParser.getArgs()['intrinsicTimeModel']

    dP = DispatcherComponentTester(podNum, parallelMode, baseSFCNum=baseSFCNum, topoType=topoType)
    dP.processLocalRequests(problemInstanceFilePath, enlargeTimes, expNum, mappingType, intrinsicTimeModel)
