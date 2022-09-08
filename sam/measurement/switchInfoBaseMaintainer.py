#!/usr/bin/python
# -*- coding: UTF-8 -*-

import random
from typing import Any, Dict, Union

from sam.base.acl import ACLTable
from sam.base.xibMaintainer import XInfoBaseMaintainer
from sam.base.switch import SWITCH_TYPE_DCNGATEWAY, Switch
from sam.base.messageAgent import SIMULATOR_ZONE, TURBONET_ZONE
from sam.base.vnf import VNF, VNF_TYPE_FW, VNF_TYPE_MONITOR, VNF_TYPE_RATELIMITER


class SwitchInfoBaseMaintainer(XInfoBaseMaintainer):
    def __init__(self):
        super(SwitchInfoBaseMaintainer, self).__init__()
        self._switches = {}     # type: Dict[Union[TURBONET_ZONE, SIMULATOR_ZONE], Dict[int, Dict[str, Any]]]
        # [zoneName][switchID] = {'switch':switch, 'Active':True, 'Status':none}
        self._switchesReservedResources = {}
        self._gatewaySwitchIDDict = {}
        self.isSwitchInfoInDB = False

    def _initSwitchTable(self):
        # self.dbA.dropTable("Switch")
        if not self.dbA.hasTable("Measurer", "Switch"):
            self.dbA.createTable("Switch",
                """
                ID INT UNSIGNED AUTO_INCREMENT,
                ZONE_NAME VARCHAR(100) NOT NULL,
                SWITCH_ID SMALLINT,
                SWITCH_TYPE VARCHAR(36),
                PROGRAMMABLE_FLAG TINYINT(1),
                TOTAL_TCAM SMALLINT,
                TCAM_USAGE SMALLINT,
                PICKLE BLOB,
                submission_time TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY ( ID )
                """
                )
        self.isSwitchInfoInDB = True

    def hasSwitch(self, switchID, zoneName):
        if self.isSwitchInfoInDB:
            results = self.dbA.query("Switch", " SWITCH_ID ",
                        " SWITCH_ID = '{0}' AND ZONE_NAME = '{1}'".format(
                                                        switchID, zoneName))
            if results != ():
                return True
            else:
                return False
        else:
            if switchID in self._switches[zoneName].keys():
                return True
            else:
                return False

    def addSwitch(self, switch, zoneName):
        if self.isSwitchInfoInDB:
            if not self.hasSwitch(switch.switchID, zoneName):
                self.dbA.insert("Switch",
                    " ZONE_NAME, SWITCH_ID, SWITCH_TYPE, PROGRAMMABLE_FLAG," \
                    " TOTAL_TCAM, TCAM_USAGE, PICKLE ",
                        (
                            zoneName,
                            switch.switchID,
                            switch.switchType,
                            int(bool(switch.programmable)),
                            switch.tcamSize,
                            switch.tcamUsage,
                            self.pIO.obj2Pickle(switch)
                        )
                    )
        else:
            if zoneName not in self._switches:
                self._switches[zoneName] = {}
            switchID = switch.switchID
            self._switches[zoneName][switchID] = {'switch':switch, 'Active':True, 'Status':None}

    def delSwitch(self, switchID, zoneName):
        if self.isSwitchInfoInDB:
            if self.hasSwitch(switchID, zoneName):
                self.dbA.delete("Switch",
                    " SWITCH_ID = '{0}' AND ZONE_NAME = '{1}'".format(
                                                    switchID, zoneName))
        else:
            del self._switches[zoneName][switchID]

    def getAllSwitch(self):
        switchList = []
        if self.isSwitchInfoInDB:
            results = self.dbA.query("Switch",
                        " ID, ZONE_NAME, SWITCH_ID, SWITCH_TYPE, PROGRAMMABLE_FLAG," \
                        " TOTAL_TCAM, TCAM_USAGE, PICKLE ")
            for switch in results:
                switchList.append(switch)
        else:
            for zoneName, switchsInfo in self._switches.items():
                for switchID, switchInfo in switchsInfo.items():
                    switchList.append(switchInfo['switch'])
        return switchList

    def updateSwitchesInAllZone(self, switches):
        self._switches = switches

    def updateSwitchesByZone(self, switches, zoneName):
        if zoneName not in self._switches.keys():
            self._switches[zoneName] = {}
        self._switches[zoneName] = switches

    def updateSwitchState(self, switchID, zoneName, state):
        self._switches[zoneName][switchID]['Active'] = state

    def getSwitchesInAllZone(self):
        return self._switches

    def getSwitchesByZone(self, zoneName, pruneInactiveSwitches=False):
        if pruneInactiveSwitches:
            switches = {}
            for switchID, switchInfoDict in self._switches[zoneName].items():
                if switchInfoDict['Active']:
                    switches[switchID] = switchInfoDict
            return switches
        else:
            return self._switches[zoneName]

    def getInactiveSwitchesByZone(self, zoneName):
        switches = {}
        for switchID, switchInfoDict in self._switches[zoneName].items():
            if not switchInfoDict['Active']:
                switches[switchID] = switchInfoDict
        return switches

    def getSpecificTypeOfSwitchByZone(self, zoneName, switchType):
        switchList = []
        for switchID in self._switches[zoneName]:
            switch = self._switches[zoneName][switchID]["switch"]
            switchActive = self._switches[zoneName][switchID]['Active']
            if (switch.switchType == switchType
                    and switchActive):
                switchList.append(switch)
        return switchList

    def isSwitchID(self, nodeID):
        switches = self.getSwitchesInAllZone()
        for switchesInAZoneDict in switches.values():
            if nodeID in switchesInAZoneDict.keys():
                return True
        else:
            return False

    def isSwitchActive(self, switchID, zoneName):
        # type: (int, str) -> bool
        return self._switches[zoneName][switchID]['Active']

    def getSwitch(self, switchID, zoneName):
        # type: (int, str) -> Switch
        return self._switches[zoneName][switchID]['switch']

    def reserveSwitchResource(self, switchID, reservedTcamUsage, zoneName):
        if not (zoneName in self._switchesReservedResources):
            self._switchesReservedResources[zoneName] = {}
        if not (switchID in self._switchesReservedResources[zoneName]):
            self._switchesReservedResources[zoneName][switchID] = {}
            self._switchesReservedResources[zoneName][switchID]["tcamUsage"] = reservedTcamUsage
        else:
            tcamUsage = self._switchesReservedResources[zoneName][switchID]["tcamUsage"]
            self._switchesReservedResources[zoneName][switchID]["tcamUsage"] = tcamUsage \
                + reservedTcamUsage

    def releaseSwitchResource(self, switchID, releaseTcamUsage, zoneName):
        if not (zoneName in self._switchesReservedResources):
            self._switchesReservedResources[zoneName] = {}
        if not (switchID in self._switchesReservedResources[zoneName]):
            raise ValueError("Unknown switchID:{0}".format(switchID))
        else:
            tcamUsage = self._switchesReservedResources[zoneName][switchID]["tcamUsage"]
            self._switchesReservedResources[zoneName][switchID]["tcamUsage"] = tcamUsage \
                - releaseTcamUsage

    def getSwitchReservedResource(self, switchID, zoneName):
        if not (zoneName in self._switchesReservedResources):
            self._switchesReservedResources[zoneName] = {}
        if not (switchID in self._switchesReservedResources[zoneName]):
            # raise ValueError("Unknown switchID:{0}".format(switchID))
            self.reserveSwitchResource(switchID, 0, zoneName)
        return self._switchesReservedResources[zoneName][switchID]["tcamUsage"]

    def getSwitchResidualResource(self, switchID, zoneName):
        reservedTCAMUsage = self.getSwitchReservedResource(switchID, zoneName)
        switch = self.getSwitch(switchID, zoneName)
        tcamCapacity = switch.tcamSize
        return tcamCapacity - reservedTCAMUsage

    def hasEnoughSwitchResource(self, switchID, expectedTCAM, zoneName):
        # TCAM resources
        switch = self.getSwitch(switchID, zoneName)
        tCAMCapacity = switch.tcamSize
        reservedTCAM = self.getSwitchReservedResource(
            switchID, zoneName)
        residualTCAM = tCAMCapacity - reservedTCAM
        # self.logger.debug(
        #     "switch resource, tCAMCapacity:{0}, reservedTCAM:{1}, expectedTCAM:{2}".format(
        #         tCAMCapacity, reservedTCAM, expectedTCAM
        #     ))
        if residualTCAM > expectedTCAM:
            return True
        else:
            return False

    def hasEnoughP4SwitchResources(self, switchID, vnf, zoneName):
        # type: (int, VNF, str) -> bool
        switch = self.getSwitch(switchID, zoneName)
        vnfType = vnf.vnfType
        p4NFUsage = switch.p4NFUsage
        if vnfType == VNF_TYPE_FW:
            aclTable = vnf.config # type: ACLTable
            v4RulesNum = aclTable.getIPv4RulesNum()
            v6RulesNum = aclTable.get128BitsRulesNum()
            condition0 = p4NFUsage.hasEnoughV4FirewallResource(v4RulesNum)
            condition1 = p4NFUsage.hasEnoughV6FirewallResource(v6RulesNum)
            return condition0 and condition1
        elif vnfType == VNF_TYPE_MONITOR:
            return p4NFUsage.hasEnoughMonitorResource(1)
        elif vnfType == VNF_TYPE_RATELIMITER:
            return p4NFUsage.hasEnoughRatelimiterResource(1)
        else:
            return p4NFUsage.hasEnoughSFCINumResource(1)

    def randomSelectDCNGateWaySwitch(self, zoneName):
        switchList = self.getSpecificTypeOfSwitchByZone(zoneName,
                                            SWITCH_TYPE_DCNGATEWAY)
        rndIdx = random.randint(0, len(switchList)-1)
        return switchList[rndIdx]

    # def getDCNGateway(self):
    #     dcnGateway = None
    #     switchesInfoDict = self.getSwitchesByZone(self.zoneName)
    #     # self.logger.warning(switchesInfoDict)
    #     for key, switchInfoDict in switchesInfoDict.items():
    #         switch = switchInfoDict['switch']
    #         # self.logger.debug(switch)
    #         if switch.switchType == SWITCH_TYPE_DCNGATEWAY:
    #             # self.logger.debug(
    #             #     "switch.switchType:{0}".format(switch.switchType)
    #             #     )
    #             dcnGateway = switch
    #             break
    #     else:
    #         raise ValueError("Find DCN Gateway failed")
    #     return dcnGateway
