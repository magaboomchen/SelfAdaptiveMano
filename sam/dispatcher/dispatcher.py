#!/usr/bin/python
# -*- coding: UTF-8 -*-

import time
import math
import copy
import numpy as np

from sklearn import datasets, linear_model
from sklearn.metrics import mean_squared_error, r2_score

from sam.base.messageAgent import *
from sam.base.command import *
from sam.base.pickleIO import PickleIO
from sam.base.shellProcessor import ShellProcessor
from sam.orchestration import orchestrator
from sam.dispatcher.argParser import ArgParser
from sam.measurement.dcnInfoBaseMaintainer import DCNInfoBaseMaintainer
from sam.base.exceptionProcessor import ExceptionProcessor


class Dispatcher(object):
    def __init__(self, podNum, parallelMode=True, timeBudget=10, autoScale=False):
        self.pIO = PickleIO()
        self._dib = DCNInfoBaseMaintainer()
        self.sP = ShellProcessor()
        self.podNum = podNum
        self.topoType = "fat-tree"
        self.timeBudget = timeBudget
        self.parallelMode = parallelMode
        self.autoScale = autoScale
        self.orchestratorDict = {}  # {"name": {"oPid":pPid, "oInfoDict":oInfoDict, "dib":dib, "liveness":True, "cpuUtilList":[], "memoryUtilList":[]}}

        logConfigur = LoggerConfigurator(__name__, './log',
            'dispatcher.log', level='warning')
        self.logger = logConfigur.getLogger()

        self.dispatcherQueueName = DISPATCHER_QUEUE
        self._messageAgent = MessageAgent(self.logger)
        self._messageAgent.startRecvMsg(self.dispatcherQueueName)

        self.mediatorQueueName = MEDIATOR_QUEUE
        self._mediatorStubMsgAgent = MessageAgent(self.logger)
        self._mediatorStubMsgAgent.startRecvMsg(self.mediatorQueueName)

        self._testStartTime = None
        self._testEndTime = None
        self.resourceRecordTimeout = 2

    def processLocalRequests(self, instanceFilePath, enlargeTimes, expNum):
        self.localRequestMode = True
        self.expNum = expNum
        self.sfcLength = self.__parseSFCLength(instanceFilePath)
        self.enlargeTimes = enlargeTimes
        self._init4LocalRequests(instanceFilePath)
        self._testStartTime = time.time()
        self.startLocalRequestsRoutine()
        self.killAllOrchestratorInstances()

    def __parseSFCLength(self, instanceFilePath):
        idx1 = instanceFilePath.find("sfcLength=")
        idx2 = instanceFilePath.find(".instance")
        if idx1 != -1 and idx2 != -1:
            sfcLength = int(instanceFilePath[idx1+len("sfcLength="):idx2])
        else:
            sfcLength = 7
        return sfcLength

    def test_parseSFCLength(self):
        filePath = "../instance/instance/fat-tree/0/fat-tree-k=22_V=11.sfcr_set_M=1000.sfcLength=5.instance"
        print(self._parseSFCLength(filePath))

    def _init4LocalRequests(self, instanceFilePath):
        self._loadInstance(instanceFilePath)
        self._enlargeRequests()
        self._updateRequestToMsgQueue()
        self._updateDib()
        # decide the orchestrator number and corresponding idx;
        maxPodNumPerOrchstratorInstance = self._computeOrchestratorInstanceMaxPodNum(
                        len(self.addSFCIRequests) * (self.enlargeTimes-1))
        # init X orchestrator instances
        oInfoList = self._computeOrchInstanceInfoList(maxPodNumPerOrchstratorInstance)
        self.logger.debug("oInfoList:{0}".format(oInfoList))
        for idx,oInfoDict in enumerate(oInfoList):
            oPid = self.initNewOrchestratorInstance(idx, oInfoDict)
            self.orchestratorDict[oInfoDict["name"]] = {"oPid": oPid,
                                    "oInfoDict": oInfoDict,
                                    "dib":None, "liveness":True,
                                    "sfcDict":{}, "sfciDict":{},
                                    "cpuUtilList":[], "memoryUtilList":[]}
            # TODO: put dib into new orchestrator instance
            self.putState2Orchestrator(oInfoDict["name"])
            self.turnOnOrchestrator(oInfoDict["name"])
        self.logger.debug("self.orchestratorDict: {0}".format(self.orchestratorDict))
        self.__assignSFCs2DifferentOrchestratorInstance()
        self.__dispatchInitialAddSFCIRequestToOrch()

    def __dispatchInitialAddSFCIRequestToOrch(self):
        cnt = 0
        while True:
            if cnt >= len(self.addSFCIRequests):
                break
            msgCnt = self._messageAgent.getMsgCnt(self.dispatcherQueueName)
            if self.autoScale:
                self.scalingOrchestratorInstances(msgCnt)
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

    def putState2Orchestrator(self, orchestratorName):
        cmd = Command(CMD_TYPE_PUT_ORCHESTRATION_STATE, uuid.uuid1(), attributes={"dib":self._dib})
        queueName = "ORCHESTRATOR_QUEUE_{0}".format(orchestratorName)
        self.sendCmd(cmd, queueName)

    def turnOnOrchestrator(self, orchestratorName):
        cmd = Command(CMD_TYPE_TURN_ORCHESTRATION_ON, uuid.uuid1(), attributes={})
        queueName = "ORCHESTRATOR_QUEUE_{0}".format(orchestratorName)
        self.sendCmd(cmd, queueName)

    def sendCmd(self, cmd, queueName):
        msg = SAMMessage(MSG_TYPE_DISPATCHER_CMD, cmd)
        self._messageAgent.sendMsg(queueName, msg)

    def __assignSFCs2DifferentOrchestratorInstance(self):
        # divide all request equally, and assign their SFC into different orchestrator instance in self.orchestratorDict
        self.orchestratorNum = len(self.orchestratorDict)
        self.requestPerOrchestrator = math.ceil(len(self.addSFCIRequests) / self.orchestratorNum)
        candidateOrchList = self.orchestratorDict.keys()
        for idx,addSFCIReq in enumerate(self.addSFCIRequests):
            sfc = addSFCIReq.attributes['sfc']
            orchName = candidateOrchList[idx%len(candidateOrchList)]
            self.orchestratorDict[orchName]["sfcDict"][sfc.sfcUUID] = sfc
        # self.logger.info("self.orchestratorDict:{0}".format(self.orchestratorDict))

    def _computeOrchInstanceInfoList(self, maxPodNumPerOrchstratorInstance):
        self.logger.warning("maxPodNumPerOrchstratorInstance:{0}".format(maxPodNumPerOrchstratorInstance))
        oPodNumList = []
        totalPodNum = self.podNum
        self.logger.debug("totalPodNum:{0}".format(totalPodNum))
        while totalPodNum > 0:
            if totalPodNum-maxPodNumPerOrchstratorInstance >= 0:
                oPodNumList.append(maxPodNumPerOrchstratorInstance)
                totalPodNum-=maxPodNumPerOrchstratorInstance
            else:
                oPodNumList.append(totalPodNum)
                break
        oInfoList = []
        for idx,podNum in enumerate(oPodNumList):
            minPodIdx = sum(oPodNumList[:idx])
            maxPodIdx = minPodIdx + podNum - 1
            oInfoDict = {
                "name": "{0}_{1}".format(minPodIdx, maxPodIdx),
                "minPodIdx": minPodIdx,
                "maxPodIdx": maxPodIdx
            }
            oInfoList.append(oInfoDict)
        return oInfoList

    def _loadInstance(self, instanceFilePath):
        self.instance = self.pIO.readPickleFile(instanceFilePath)
        self.topologyDict = self.instance['topologyDict']
        self.addSFCIRequests = self.instance['addSFCIRequests']

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
        return base64.b64encode(pickle.dumps(message,-1))

    def _updateDib(self):
        self._dib.updateServersByZone(self.topologyDict["servers"],
            SIMULATOR_ZONE)
        self._dib.updateSwitchesByZone(self.topologyDict["switches"],
            SIMULATOR_ZONE)
        self._dib.updateLinksByZone(self.topologyDict["links"],
            SIMULATOR_ZONE)
        self._dib.updateSwitch2ServerLinksByZone(SIMULATOR_ZONE)

    def startDispatcher(self):
        raise ValueError("Haven't implement")
        self.init()
        self.startRoutine()

    def _init(self):
        pass
        # TODO: future works: must to implements for project
        # load topology, from DataBase(Redis or mysql) or from local pickle file

        # start the first orchestrator

    def startRoutine(self):
        while True:
            msgCnt = self._messageAgent.getMsgCnt(self.dispatcherQueueName)
            if self.autoScale:
                self.scalingOrchestratorInstances(msgCnt)
            msg = self._messageAgent.getMsg(self.dispatcherQueueName)
            msgType = msg.getMessageType()
            if msgType == None:
                pass
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

            # TODO: future works: keep dcn info consistency
            # sync state from orchestrator instance periodically (i.e. 5 minutes): getState(), update subZoneState into self._dib
            # store self._dib into mysql

    def startLocalRequestsRoutine(self):
        self.logger.info("Dispatch all addSFCIRequests")
        cnt = 0
        self._recordOrchUtilization()
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
                self._recordOrchUtilization()
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
                        self.logger.info("cnt:{0}".format(cnt))
                        self.logger.debug("len(self.enlargedAddSFCIRequests):{0}".format(len(self.enlargedAddSFCIRequests)))
                        self.logger.debug("len(self.addSFCIRequests):{0}".format(len(self.addSFCIRequests)))
                        if cnt >= len(self.enlargedAddSFCIRequests) - len(self.addSFCIRequests) and self.localRequestMode:
                            self._testEndTime = time.time()
                            totalOrchTime = self._testEndTime - self._testStartTime
                            res = {
                                "totalOrchTime":totalOrchTime,
                                "orchestratorDict":self.orchestratorDict
                            }
                            self.pIO.writePickleFile("./res/{0}/{1}/{2}_parallelMode={3}_sfcLength={4}_enlargeTime={5}.pickle".format(
                                    self.topoType, self.expNum, self.podNum, int(self.parallelMode), self.sfcLength, self.enlargeTimes), res)
                            break
                else:
                    self.logger.error("Unknown massage body:{0}".format(body))
            currentTime = time.time()
            if currentTime - lastTime > self.resourceRecordTimeout:
                self._recordOrchUtilization()
                lastTime = time.time()
            # else:
            #     self.logger.info("time gap: {0}".format(lastTime - currentTime))

    def _recordOrchUtilization(self):
        for orchName in self.orchestratorDict.keys():
            cpuUtil, memoryUtil = self._getOrchUtilization(orchName)
            self.logger.info("cpuUtil:{0}, memoryUtil:{1}".format(cpuUtil, memoryUtil))
            self.orchestratorDict[orchName]["cpuUtilList"].append(cpuUtil)
            self.orchestratorDict[orchName]["memoryUtilList"].append(memoryUtil)

    def _getOrchUtilization(self, orchName):
        try:
            oPid = self.orchestratorDict[orchName]["oPid"]
            cpuUtil, memoryUtil = self.sP.getProcessCPUAndMemoryUtilization(oPid)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                "dispatcher _getOrchUtilization")
        return cpuUtil, memoryUtil

    def scalingOrchestratorInstances(self, msgCnt):
        raise ValueError("Only has design, not implementation")
        if self.parallelMode:
            # decide the new orchestators instance number: scale-in or scale-out
            maxPodNumPerOrchstratorInstance = self._computeOrchestratorInstanceMaxPodNum(msgCnt)
            oInfoList = self._computeOrchInstanceInfoList(maxPodNumPerOrchstratorInstance)
            scaleDecisionDict = self._makeScalingDecision(oInfoList)
            if scaleDecisionDict["scaleAction"] == "scale-out":
                pass
                # change existed instance podIdx by commands

                # pull and merge existed instance state into local dib

                # add x instance

                # copy local dib into new added instance

                # close scale-out process
            elif scaleDecisionDict["scaleAction"] == "scale-in":
                pass
                # pull and merge existed instance state into local dib

                # delete unwanted instance(This may need lots of time because we need to wait orchestrator instance to process its requests)

                # copy local dib into reserved instance

                # change existed instance podIdx by commands

                # close scale-in process
            else:
                pass

    def _requestHandler(self, request):
        # TODO: dispatch requests to different orchestrator instances
        try:
            if request.requestType == REQUEST_TYPE_ADD_SFC:
                pass
                # TODO: basic function
                # assign different SFC to different orchestrator in round robin mode, and
                # record which SFC has been mapped in which orchestrator instances.
                # In local test mode, we use __assignSFCs2DifferentOrchestratorInstance() to assign SFC
            elif request.requestType == REQUEST_TYPE_ADD_SFCI:
                sfc = request.attributes["sfc"]
                sfci = request.attributes["sfci"]
                orchName = self._getOrchestratorNameBySFC(sfc)      # Read from self.orchestratorDict
                self._assignSFCI2Orchestrator(sfci, orchName)       # update self.orchestratorDict
                self._sendRequest2Orchestrator(request, orchName)   # we dispatch add request previously
            elif request.requestType == REQUEST_TYPE_DEL_SFCI:
                pass
                # TODO: basic function
                # figure out which orchestrator has this SFCI
            elif request.requestType == REQUEST_TYPE_DEL_SFC:
                pass
                # TODO: basic function
                # figure out which orchestrator has this SFC
            else:
                self.logger.warning(
                    "Unknown request:{0}".format(request.requestType)
                    )
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                "dispatcher _requestHandler")
        finally:
            pass

    def _getOrchestratorNameBySFC(self, sfc):
        for orchName,oInfo in self.orchestratorDict.items():
            if oInfo["sfcDict"].has_key(sfc.sfcUUID):
                return orchName
        else:
            raise ValueError("Can't find orchestrator instance.")

    def _assignSFCI2Orchestrator(self, sfci, orchName):
        self.orchestratorDict[orchName]["sfciDict"][sfci.sfciID] = sfci

    def _sendRequest2Orchestrator(self, request, orchName):
        queueName = "ORCHESTRATOR_QUEUE_{0}".format(orchName)
        msg = SAMMessage(MSG_TYPE_REQUEST, request)
        self._messageAgent.sendMsg(queueName, msg)

    def _commandReplyHandler(self, cmd):
        raise ValueError("Unimplementation _commandReplyHandler")

    def _commandHandler(self, cmd):
        raise ValueError("Unimplementation _commandHandler")

    def _computeOrchestratorInstanceMaxPodNum(self, msgCnt):
        if not self.parallelMode:
            return self.podNum
        # load regressor
        regr = self.loadRegressor(self.podNum)
        # predict orchestration instances number
        if self.topoType == "fat-tree":
            switchNum, torSwitchNum, serverNum = self._getFatTreeNodesNumber(self.podNum)
        self.maxBW = 100
        self.maxSFCLength = 7
        X_real = [[switchNum * (serverNum + torSwitchNum + self.podNum) * self.maxBW * self.maxSFCLength * msgCnt]]
        X_real = np.array(X_real)
        Y_real = max(regr.predict(X_real)[0], 1)
        minOrchestratorNum = max(math.pow( Y_real/self.timeBudget, 1/3.0 ), 1)
        self.logger.warning("minOrchestratorNum:{0}".format(minOrchestratorNum))
        maxPodNumPerOrchstratorInstance = math.floor(self.podNum / minOrchestratorNum)
        return max(int(maxPodNumPerOrchstratorInstance),1)

    def loadRegressor(self, podNum):
        regressorFilePath = self.getRegressorFilePath()
        regr = self.pIO.readPickleFile(regressorFilePath)
        return regr

    def _getFatTreeNodesNumber(self, podNum):
        switchNum = int(math.pow(podNum/2, 2) + math.pow(podNum, 2))
        serverNum = int(math.pow(podNum, 3))
        torSwitchNum = int(math.pow(podNum, 2) / 2)
        return [switchNum, torSwitchNum, serverNum]

    def getRegressorFilePath(self):
        idx = __file__.rfind('/')
        return "{0}/regressor/{1}".format(__file__[:idx], self.podNum)

    def _makeScalingDecision(self, oInfoList):
        raise ValueError("Haven't implement!")
        targetInstanceNumber = len(oInfoList)
        # compare existed instance number and targetInstanceNumber
        scaleAction = None
        if len(self.orchestratorDict) < targetInstanceNumber:
            scaleAction = "scale-out"
            # For scale-out, generate existed instance new podIdx(If there are no existed instance, then this part is None); generate new instance podIdx;
            self.orchestratorDict = {}  # {"idx": orchestratorInfo}
            # orchestratorInfo = {"dib":dib,"minPodIdx":minPodIdx, "maxPodIdx":maxPodIdx}
        elif len(self.orchestratorDict) > targetInstanceNumber:
            scaleAction = "scale-in"
            # For scale-in, generate existed instance new podIdx; generate delete which existed instance;

        else:
            scaleAction = None
        scaleDecisionDict = {
            "scaleAction": scaleAction,
        }
        return scaleDecisionDict

    def initNewOrchestratorInstance(self, idx, oInfoDict):
        self.logger.info("initNewOrchestratorInstance instance name:{0}".format(oInfoDict["name"]))
        tasksetCmd = "taskset -c {0}".format(idx)
        orchestratorFilePath = self.__getOrchestratorFilePath()
        self.logger.info(orchestratorFilePath)
        args = "-name {0} -p {1} -minPIdx {2} -maxPIdx {3} -turnOff".format(oInfoDict["name"], self.podNum,
                                            oInfoDict["minPodIdx"] , oInfoDict["maxPodIdx"])
        commandLine = "{0} {1}".format(orchestratorFilePath, args)
        self.sP.runPythonScript(commandLine, cmdPrefix=tasksetCmd)
        time.sleep(0.0000001)
        return self.sP.getPythonScriptProcessPid(commandLine)

    def killAllOrchestratorInstances(self):
        for orchName in self.orchestratorDict.keys():
            self.turnOffOrchestrationInstance(orchName)

    def __getOrchestratorFilePath(self):
        filePath = orchestrator.__file__
        directoryPath = self.getFileDirectory(filePath)
        # self.logger.info(directoryPath)
        return directoryPath + '/orchestrator.py'

    def getFileDirectory(self, filePath):
        index = filePath.rfind('/')
        directoryPath = filePath[0:index]
        return directoryPath

    def turnOffOrchestrationInstance(self, orchestratorName):
        pass
        # TODO: future works: auto orchestrator scaling
        # kill orchestrator process itself by sending a kill command; orchestrator reply kill command to comfirm the kill.
        # Cautions: we need to wait orchestrator to process its requests
        # dispatcher update instance state in this class
        cmd = Command(CMD_TYPE_KILL_ORCHESTRATION, uuid.uuid1(), attributes={})
        queueName = "ORCHESTRATOR_QUEUE_{0}".format(orchestratorName)
        self.sendCmd(cmd, queueName)

    def migrateState(self, srcInstanceIdx, dstInstanceIdx):
        pass
        # TODO: future works: auto orchestrator scaling


if __name__ == "__main__":
    argParser = ArgParser()
    problemInstanceFilePath = argParser.getArgs()['pFilePath']
    podNum = argParser.getArgs()['p']   # example: 36
    enlargeTimes = argParser.getArgs()['et']
    localTest = argParser.getArgs()['localTest']
    parallelMode = argParser.getArgs()['parallelMode']
    expNum = argParser.getArgs()['expNum']

    dP = Dispatcher(podNum, parallelMode)
    if localTest:
        dP.processLocalRequests(problemInstanceFilePath, enlargeTimes, expNum)
    else:
        dP.startDispatcher()
