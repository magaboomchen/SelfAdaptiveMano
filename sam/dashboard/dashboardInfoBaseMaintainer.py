#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.databaseAgent import DatabaseAgent
from sam.base.xibMaintainer import XInfoBaseMaintainer


class DashboardInfoBaseMaintainer(XInfoBaseMaintainer):
    def __init__(self, host, user, passwd):
        super(DashboardInfoBaseMaintainer, self).__init__()
        self.addDatabaseAgent(host, user, passwd)
        self.dbA.connectDB(db = "Dashboard")
        self._initZoneTable()
        self._initUserTable()
        self._initRoutingSchemeTable()

    def _initZoneTable(self):
        if not self.dbA.hasTable("Dashboard", "Zone"):
            self.dbA.createTable("Zone",
                # id(pKey), Zone_Name
                """
                ID INT UNSIGNED AUTO_INCREMENT,
                ZONE_NAME VARCHAR(100) NOT NULL,
                submission_time TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY ( ID )
                """
                )

    def addZone(self, zoneName):
        if not self.hasZone(zoneName):
            self.dbA.insert("Zone", " ZONE_NAME ", "'{0}'".format(zoneName))

    def hasZone(self, zoneName):
        results = self.dbA.query("Zone", " ZONE_NAME ", " ZONE_NAME = '{0}'".format(
            zoneName))
        if results != ():
            return True
        else:
            return False

    def delZone(self, zoneName):
        if self.hasZone(zoneName):
            self.dbA.delete("Zone", " ZONE_NAME = '{0}'".format(zoneName))

    def getAllZone(self):
        results = self.dbA.query("Zone", " ZONE_NAME ")
        zoneList = []
        for zone in results:
            zoneList.append(zone[0])
        return zoneList

    def _initUserTable(self):
        if not self.dbA.hasTable("Dashboard", "User"):
            self.dbA.createTable("User",
                # id(pKey), Zone_Name
                """
                ID INT UNSIGNED AUTO_INCREMENT,
                USER_NAME VARCHAR(100) NOT NULL,
                USER_UUID VARCHAR(36),
                submission_time TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY ( ID )
                """
                )

    def addUser(self, userName, userUUID):
        if not self.hasUser(userUUID):
            self.dbA.insert("User", " USER_NAME, USER_UUID ", "'{0}', '{1}'".format(userName, userUUID))

    def hasUser(self, userUUID):
        results = self.dbA.query("User", " USER_UUID ", " USER_UUID = '{0}'".format(
            userUUID))
        if results != ():
            return True
        else:
            return False

    def delUser(self, userUUID):
        if self.hasUser(userUUID):
            self.dbA.delete("User", " USER_UUID = '{0}'".format(userUUID))

    def getAllUser(self):
        results = self.dbA.query("User", " USER_NAME ")
        userList = []
        for userName in results:
            userList.append(userName[0])
        return userList

    def _initRoutingSchemeTable(self):
        raise ValueError("Unimplementation!")

    def addRoutingScheme(self, xxx):
        pass

    def hasRoutingScheme(self, xxx):
        pass

    def delRoutingScheme(self, xxx):
        pass

    def getAllRoutingScheme(self, xxx):
        pass
