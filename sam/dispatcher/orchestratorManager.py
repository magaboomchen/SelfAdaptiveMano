#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid
import time
import math
import numpy as np

import psutil

from sam.base.messageAgent import MessageAgent, SAMMessage, \
                                    MSG_TYPE_DISPATCHER_CMD
from sam.base.command import CMD_TYPE_ORCHESTRATION_UPDATE_EQUIPMENT_STATE, \
                Command, CMD_TYPE_PUT_ORCHESTRATION_STATE, \
                CMD_TYPE_TURN_ORCHESTRATION_ON, CMD_TYPE_KILL_ORCHESTRATION
from sam.base.pickleIO import PickleIO
from sam.orchestration import orchestrator
from sam.base.shellProcessor import ShellProcessor
from sam.base.loggerConfigurator import LoggerConfigurator
from sam.dispatcher.config import CONSTANT_ORCHESTRATOR_NUM, TIME_BUDGET, \
                                    ORCHESTRATOR_PROCESS_STARTUP_TIME
from sam.orchestration.oConfig import BATCH_SIZE, MAX_SFC_LENGTH
from sam.measurement.dcnInfoBaseMaintainer import DCNInfoBaseMaintainer
from sam.base.exceptionProcessor import ExceptionProcessor


class OrchestratorManager(object):
    def __init__(self, parallelMode, zoneName, podNum, topoType):
        self.sP = ShellProcessor()
        self._dib = DCNInfoBaseMaintainer()
        self.pIO = PickleIO()

        self.orchestratorDict = {}  # {"name": {"oPid":pPid, "oInfoDict":oInfoDict, "dib":dib, "liveness":True, "cpuUtilList":[], "memoryUtilList":[]}}
        self.zoneName = zoneName
        self.podNum = podNum
        self.topoType = topoType
        self.roundRobinCounter = 0

        self.parallelMode = parallelMode
        self.timeBudget = TIME_BUDGET
        self.constantOrchestratorNum = CONSTANT_ORCHESTRATOR_NUM

        logConfigur = LoggerConfigurator(__name__, './log',
            'orchManager_{0}.log'.format(self.zoneName), level='debug')
        self.logger = logConfigur.getLogger()

        self._messageAgent = MessageAgent(self.logger)

    def addOrchInstance(self, oInfoDictName, oPid, oInfoDict):
        self.orchestratorDict[oInfoDictName] = {
                                "oPid": oPid,
                                "oInfoDict": oInfoDict,
                                "dib":None, "liveness":True,
                                "sfcDict":{}, "sfciDict":{},
                                "cpuUtilList":[], "memoryUtilList":[],
                                "totalCPUUtilList":[]
                            }

    def getOrchInstanceNum(self):
        return len(self.orchestratorDict)

    def _selectOrchInRoundRobin(self):
        candidateOrchList = sorted(self.orchestratorDict.keys())
        orchName = candidateOrchList[self.roundRobinCounter%len(candidateOrchList)]
        self.roundRobinCounter = (self.roundRobinCounter + 1)%self.getOrchInstanceNum()
        return orchName

    def getOrchestratorDict(self):
        return self.orchestratorDict

    def assignSFC2OrchInstance(self, addSFCIRequests):
        candidateOrchList = self.orchestratorDict.keys()
        for idx,addSFCIReq in enumerate(addSFCIRequests):
            sfc = addSFCIReq.attributes['sfc']
            orchName = candidateOrchList[idx%len(candidateOrchList)]
            self.orchestratorDict[orchName]["sfcDict"][sfc.sfcUUID] = sfc

    def _updateDib(self, topologyDict, zoneName):
        self._dib.updateServersByZone(topologyDict["servers"],
                                        zoneName)
        self._dib.updateSwitchesByZone(topologyDict["switches"],
                                        zoneName)
        self._dib.updateLinksByZone(topologyDict["links"],
                                        zoneName)
        # self._dib.updateSwitch2ServerLinksByZone(zoneName)
        # self._dib.getAllZone()

    def putState2Orchestrator(self, orchestratorName):
        # self.logger.info("dib: {0}".format(self._dib))
        cmd = Command(CMD_TYPE_PUT_ORCHESTRATION_STATE, uuid.uuid1(),
                        attributes={"dib":self._dib})
        queueName = "ORCHESTRATOR_QUEUE_{0}".format(orchestratorName)
        self.sendCmd(cmd, queueName)

    def updateEquipmentState2Orchestrator(self, orchestratorName, detectionDict):
        cmd = Command(CMD_TYPE_ORCHESTRATION_UPDATE_EQUIPMENT_STATE, uuid.uuid1(),
                        attributes={"detectionDict":detectionDict})
        queueName = "ORCHESTRATOR_QUEUE_{0}".format(orchestratorName)
        self.sendCmd(cmd, queueName)

    def turnOnOrchestrator(self, orchestratorName):
        cmd = Command(CMD_TYPE_TURN_ORCHESTRATION_ON, uuid.uuid1(),
                        attributes={})
        queueName = "ORCHESTRATOR_QUEUE_{0}".format(orchestratorName)
        self.sendCmd(cmd, queueName)

    def sendCmd(self, cmd, queueName):
        msg = SAMMessage(MSG_TYPE_DISPATCHER_CMD, cmd)
        self._messageAgent.sendMsg(queueName, msg)

    def computeOrchInfoList(self):
        if self.topoType == "fat-tree":
            maxPodNumPerOrchstratorInstance = self._computeOrchestratorInstanceMaxPodNum(BATCH_SIZE)
            minOrchNum = self._computeOrchestratorInstanceMaxOrchNum(BATCH_SIZE)
            self.logger.info("maxPodNumPerOrchstratorInstance is {0}, minOrchNum is {1}".format(maxPodNumPerOrchstratorInstance, minOrchNum))
            # init X orchestrator instances
            oInfoList = self._computeOrchInstanceInfoList(maxPodNumPerOrchstratorInstance, minOrchNum)
            self.logger.info(oInfoList)
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

        return oInfoList

    def _computeOrchInstanceInfoList(self, maxPodNumPerOrchstratorInstance, minOrchNum):
        self.logger.warning("maxPodNumPerOrchstratorInstance:{0}".format(maxPodNumPerOrchstratorInstance))

        self.logger.warning("minOrchNum:{0}".format(minOrchNum))
        oPodNumList = self.splitInteger(self.podNum, minOrchNum)

        self.logger.warning("orch pod number distribution: {0}".format(oPodNumList))

        oInfoList = []
        for idx,podNum in enumerate(oPodNumList):
            minPodIdx = sum(oPodNumList[:idx])
            maxPodIdx = minPodIdx + podNum - 1
            oInfoDict = {
                "name": "{0}_{1}_{2}".format(self.zoneName, minPodIdx, maxPodIdx),
                "minPodIdx": minPodIdx,
                "maxPodIdx": maxPodIdx
            }
            oInfoList.append(oInfoDict)
        return oInfoList

    def splitInteger(self, x, n):
        res = []
        # If we cannot split the
        # number into exactly 'N' parts
        if(x < n):
            raise ValueError("X < N")
    
        # If x % n == 0 then the minimum
        # difference is 0 and all
        # numbers are x / n
        elif (x % n == 0):
            for i in range(n):
                res.append(x//n)
        else:
            # upto n-(x % n) the values
            # will be x / n
            # after that the values
            # will be x / n + 1
            zp = n - (x % n)
            pp = x//n
            for i in range(n):
                if(i>= zp):
                    res.append(pp + 1)
                else:
                    res.append(pp)
        return res

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

    def _getOrchestratorNameBySFC(self, sfc):
        for orchName, oInfo in self.orchestratorDict.items():
            if sfc.sfcUUID in oInfo["sfcDict"]:
                return orchName
        else:
            raise ValueError("Can't find orchestrator instance.")

    def _assignSFC2Orchestrator(self, sfc, orchName):
        self.orchestratorDict[orchName]["sfcDict"][sfc.sfcUUID] = sfc

    def _assignSFCI2Orchestrator(self, sfci, orchName):
        self.orchestratorDict[orchName]["sfciDict"][sfci.sfciID] = sfci

    def _computeOrchestratorInstanceMaxPodNum(self, msgCnt):
        if not self.parallelMode:
            return self.podNum
        if self.podNum == 4:
            return self.podNum
        # predict orchestration instances number
        self.logger.info("podNum is {0}".format(self.podNum))
        if self.topoType == "fat-tree":
            switchNum, torSwitchNum, serverNum = self._getFatTreeNodesNumber(self.podNum)
            serverNum = self._dib.getServersNumByZone(self.zoneName)
            self.logger.info("switchNum is {0}, torSwitchNum is {1}, serverNum is {2}".format(switchNum, torSwitchNum, serverNum))
        else:
            raise ValueError("Unknown topo type {0}".format(self.topoType))
        minOrchestratorNum = self.__computeMinOrchestratorNum(switchNum, msgCnt)
        self.logger.warning("minOrchestratorNum:{0}".format(minOrchestratorNum))
        maxPodNumPerOrchstratorInstance = math.floor(self.podNum / minOrchestratorNum)
        return max(int(maxPodNumPerOrchstratorInstance),1)

    def _computeOrchestratorInstanceMaxOrchNum(self, msgCnt):
        if not self.parallelMode:
            return 1
        if self.podNum == 4:
            return 1
        # predict orchestration instances number
        if self.topoType == "fat-tree":
            switchNum, torSwitchNum, serverNum = self._getFatTreeNodesNumber(self.podNum)
            serverNum = self._dib.getServersNumByZone(self.zoneName)
        else:
            raise ValueError("Unknown topo type {0}".format(self.topoType))
        minOrchestratorNum = self.__computeMinOrchestratorNum(switchNum, msgCnt)
        return int(minOrchestratorNum)

    def __computeMinOrchestratorNum(self, switchNum, msgCnt):
        if self.constantOrchestratorNum == -1:
            # load regressor
            regr = self.loadRegressor()
            # load 
            self.maxSFCLength = MAX_SFC_LENGTH
            X_real = [[switchNum * self.maxSFCLength * msgCnt]]
            X_real = np.array(X_real)
            Y_real = max(regr.predict(X_real)[0], 1)
            minOrchestratorNum = math.ceil( max(math.pow( Y_real/self.timeBudget, 1/2.0 ), 1) )
        else:
            minOrchestratorNum = self.constantOrchestratorNum

        return minOrchestratorNum

    def loadRegressor(self):
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
        # tasksetCmd = "taskset -c {0}".format(idx)
        tasksetCmd = " "
        orchestratorFilePath = self.__getOrchestratorFilePath()
        self.logger.info(orchestratorFilePath)
        args = "-name {0} -p {1} -minPIdx {2} -maxPIdx {3} -topoType {4} -zoneName {5} -turnOff".format(oInfoDict["name"], self.podNum,
                                            oInfoDict["minPodIdx"] , oInfoDict["maxPodIdx"], self.topoType, self.zoneName)
        commandLine = "{0} {1}".format(orchestratorFilePath, args)
        self.sP.runPythonScript(commandLine, cmdPrefix=tasksetCmd)
        time.sleep(ORCHESTRATOR_PROCESS_STARTUP_TIME)
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

    def _recordOrchUtilization(self):
        for orchName in self.orchestratorDict.keys():
            cpuUtil, totalCPUUtil, memoryUtil = self._getOrchUtilization(orchName)
            self.logger.info("cpuUtil:{0}, totalCPUUtil:{1}, memoryUtil:{2}".format(cpuUtil, totalCPUUtil, memoryUtil))
            self.orchestratorDict[orchName]["cpuUtilList"].append(cpuUtil)
            self.orchestratorDict[orchName]["totalCPUUtilList"].append(totalCPUUtil)
            self.orchestratorDict[orchName]["memoryUtilList"].append(memoryUtil)

    def _getOrchUtilization(self, orchName):
        try:
            oPid = self.orchestratorDict[orchName]["oPid"]
            cpuUtil, memoryUtil = self.sP.getProcessCPUAndMemoryUtilization(oPid)
            totalCPUUtil = psutil.cpu_percent(1)
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex,
                "dispatcher _getOrchUtilization")
        return cpuUtil, totalCPUUtil, memoryUtil
