#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.xibMaintainer import XInfoBaseMaintainer


class DashboardInfoBaseMaintainer(XInfoBaseMaintainer):
    def __init__(self, host, user, passwd):
        super(DashboardInfoBaseMaintainer, self).__init__()
        self.addDatabaseAgent(host, user, passwd)
        self.dbA.connectDB(db = "Dashboard")
        self._initZoneTable()
    
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
