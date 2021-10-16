#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.xibMaintainer import XInfoBaseMaintainer


class DashboardInfoBaseMaintainer(XInfoBaseMaintainer):
    def __init__(self, host, user, passwd):
        super(DashboardInfoBaseMaintainer, self).__init__()
        self.addDatabaseAgent(host, user, passwd)
        self.dbA.connectDB(db = "Dashboard")
        self._initZoneTable()
        self._initUserTable()
        self._initRoutingMorphicTable()

    def _initZoneTable(self):
        if not self.dbA.hasTable("Dashboard", "Zone"):
            self.dbA.createTable("Zone",
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
        results = self.dbA.query("Zone", " ZONE_NAME ",
                                    " ZONE_NAME = '{0}'".format(zoneName))
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
            zoneList.append(zone)
        return zoneList

    def _initUserTable(self):
        # self.dbA.dropTable("User")
        if not self.dbA.hasTable("Dashboard", "User"):
            self.dbA.createTable("User",
                """
                ID INT UNSIGNED AUTO_INCREMENT,
                USER_NAME VARCHAR(100) NOT NULL,
                USER_UUID VARCHAR(36),
                USER_TYPE VARCHAR(36) NOT NULL,
                PICKLE BLOB,
                submission_time TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY ( ID )
                """
                )

    def addUser(self, user):
        if not self.hasUser(user.userID):
            self.dbA.insert("User", " USER_NAME, USER_UUID, USER_TYPE, PICKLE ",
                                "'{0}', '{1}', '{2}', '{3}'".format(user.userName,
                                                    user.userID,
                                                    user.userType,
                                                    self.pIO.obj2Pickle(user)))

    def hasUser(self, userUUID):
        results = self.dbA.query("User", " USER_UUID ",
                                    " USER_UUID = '{0}'".format(userUUID))
        if results != ():
            return True
        else:
            return False

    def delUser(self, userUUID):
        if self.hasUser(userUUID):
            self.dbA.delete("User", " USER_UUID = '{0}'".format(userUUID))

    def getAllUser(self):
        results = self.dbA.query("User", " USER_NAME, USER_UUID, USER_TYPE, PICKLE ")
        userList = []
        for userName in results:
            userList.append(userName)
        return userList

    def _initRoutingMorphicTable(self):
        # self.dbA.dropTable("RoutingMorphic")
        if not self.dbA.hasTable("Dashboard", "RoutingMorphic"):
            self.dbA.createTable("RoutingMorphic",
                """
                ID INT UNSIGNED AUTO_INCREMENT,
                ROUTING_MORPHIC_NAME VARCHAR(100),
                PICKLE BLOB,
                submission_time TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY ( ID )
                """
                )

    def addRoutingMorphic(self, routingMorphic):
        routingMorphicName = routingMorphic.getMorphicName()
        if not self.hasRoutingMorphic(routingMorphicName):
            self.dbA.insert("RoutingMorphic", " ROUTING_MORPHIC_NAME, PICKLE ",
                            "'{0}', '{1}'".format(routingMorphicName,
                                    self.pIO.obj2Pickle(routingMorphic)))

    def hasRoutingMorphic(self, routingMorphicName):
        results = self.dbA.query("RoutingMorphic", " ROUTING_MORPHIC_NAME ",
            " ROUTING_MORPHIC_NAME = '{0}'".format(routingMorphicName))
        if results != ():
            return True
        else:
            return False

    def delRoutingMorphic(self, routingMorphic):
        routingMorphicName = routingMorphic.getMorphicName()
        if self.hasRoutingMorphic(routingMorphicName):
            self.dbA.delete("RoutingMorphic",
                                " ROUTING_MORPHIC_NAME = '{0}'".format(
                                    routingMorphicName))

    def getAllRoutingMorphic(self):
        results = self.dbA.query("RoutingMorphic", " ROUTING_MORPHIC_NAME ")
        rmList = []
        for rm in results:
            rmList.append(rm)
        return rmList
