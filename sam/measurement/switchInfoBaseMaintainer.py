#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.xibMaintainer import XInfoBaseMaintainer


class SwitchInfoBaseMaintainer(XInfoBaseMaintainer):
    def __init__(self):
        super(SwitchInfoBaseMaintainer, self).__init__()
        self._switches = {} # [zoneName][switchID] = {'switch':switch, 'active':True/False, 'status':none}
        self._switchesReservedResources = {}

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

    def hasSwitch(self, switchID, zoneName):
        results = self.dbA.query("Switch", " SWITCH_ID ",
                    " SWITCH_ID = '{0}' AND ZONE_NAME = '{1}'".format(
                                                    switchID, zoneName))
        if results != ():
            return True
        else:
            return False

    def addSwitch(self, switch, zoneName):
        if not self.hasSwitch(switch.switchID, zoneName):
            self.dbA.insert("Switch",
                " ZONE_NAME, SWITCH_ID, SWITCH_TYPE, PROGRAMMABLE_FLAG," \
                " TOTAL_TCAM, TCAM_USAGE, PICKLE ",
                " '{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}' ".format(zoneName,
                                switch.switchID,
                                switch.switchType,
                                int(bool(switch.programmable)),
                                switch.tcamSize,
                                switch.tcamUsage,
                                self.pIO.obj2Pickle(switch)
                ))

    def delSwitch(self, switchID, zoneName):
        if self.hasSwitch(switchID, zoneName):
            self.dbA.delete("Switch",
                " SWITCH_ID = '{0}' AND ZONE_NAME = '{1}'".format(
                                                switchID, zoneName))

    def getAllSwitch(self):
        results = self.dbA.query("Switch",
                    " ID, ZONE_NAME, SWITCH_ID, SWITCH_TYPE, PROGRAMMABLE_FLAG," \
                    " TOTAL_TCAM, TCAM_USAGE, PICKLE ")
        switchList = []
        for switch in results:
            switchList.append(switch)
        return switchList
                
    def updateSwitchesInAllZone(self, switches):
        self._switches = switches

    def updateSwitchesByZone(self, switches, zoneName):
        self._switches[zoneName] = switches

    def getSwitchesInAllZone(self):
        return self._switches

    def getSwitchesByZone(self, zoneName):
        return self._switches[zoneName]

    def isSwitchID(self, nodeID):
        switches = self.getSwitchesInAllZone()
        for switchesInAZoneDict in switches.values():
            if nodeID in switchesInAZoneDict.keys():
                return True
        else:
            return False

    def getSwitch(self, switchID, zoneName):
        return self._switches[zoneName][switchID]['switch']

    def reserveSwitchResource(self, switchID, reservedTcamUsage, zoneName):
        if not self._switchesReservedResources.has_key(zoneName):
            self._switchesReservedResources[zoneName] = {}
        if not self._switchesReservedResources[zoneName].has_key(switchID):
            self._switchesReservedResources[zoneName][switchID] = {}
            self._switchesReservedResources[zoneName][switchID]["tcamUsage"] = reservedTcamUsage
        else:
            tcamUsage = self._switchesReservedResources[zoneName][switchID]["tcamUsage"]
            self._switchesReservedResources[zoneName][switchID]["tcamUsage"] = tcamUsage \
                + reservedTcamUsage

    def releaseSwitchResource(self, switchID, releaseTcamUsage, zoneName):
        if not self._switchesReservedResources.has_key(zoneName):
            self._switchesReservedResources[zoneName] = {}
        if not self._switchesReservedResources[zoneName].has_key(switchID):
            raise ValueError("Unknown switchID:{0}".format(switchID))
        else:
            tcamUsage = self._switchesReservedResources[zoneName][switchID]["tcamUsage"]
            self._switchesReservedResources[zoneName][switchID]["tcamUsage"] = tcamUsage \
                - releaseTcamUsage

    def getSwitchReservedResource(self, switchID, zoneName):
        if not self._switchesReservedResources.has_key(zoneName):
            self._switchesReservedResources[zoneName] = {}
        if not self._switchesReservedResources[zoneName].has_key(switchID):
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
