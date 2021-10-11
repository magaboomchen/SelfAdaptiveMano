#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.base.xibMaintainer import XInfoBaseMaintainer


class LinkInfoBaseMaintainer(XInfoBaseMaintainer):
    def __init__(self):
        super(LinkInfoBaseMaintainer, self).__init__()
        self._links = {}    # [zoneName][(srcID,dstID)] = {'link':link, 'active':True/False, 'status':none}
        self._linksReservedResources = {}

    def _initLinkTable(self):
        # self.dbA.dropTable("Link")
        if not self.dbA.hasTable("Measurer", "Link"):
            self.dbA.createTable("Link",
                """
                ID INT UNSIGNED AUTO_INCREMENT,
                ZONE_NAME VARCHAR(100) NOT NULL,
                SRC_SWITCH_ID SMALLINT,
                DST_SWITCH_ID SMALLINT,
                TOTAL_BANDWIDTH FLOAT,
                BANDWIDTH_UTILIZATION FLOAT,
                PICKLE BLOB,
                submission_time TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY ( ID )
                """
                )

    def hasLink(self, srcID, dstID, zoneName):
        results = self.dbA.query("Link", " SRC_SWITCH_ID, DST_SWITCH_ID ",
                    " SRC_SWITCH_ID = '{0}' AND DST_SWITCH_ID = '{1}' AND ZONE_NAME = '{2}'".format(srcID, dstID, zoneName))
        if results != ():
            return True
        else:
            return False

    def addLink(self, link, zoneName):
        if not self.hasLink(link.srcID, link.dstID, zoneName):
            self.dbA.insert("Link",
                " ZONE_NAME, SRC_SWITCH_ID, DST_SWITCH_ID, TOTAL_BANDWIDTH," \
                " BANDWIDTH_UTILIZATION, PICKLE ",
                "'{0}', '{1}', '{2}', '{3}', '{4}', '{5}' ".format(zoneName,
                                link.srcID,
                                link.dstID,
                                link.bandwidth,
                                link.utilization,
                                self.pIO.obj2Pickle(link)
                ))

    def delLink(self, link, zoneName):
        if self.hasLink(link.srcID, link.dstID, zoneName):
            self.dbA.delete("Link",
                " SRC_SWITCH_ID = '{0}' AND SRC_SWITCH_ID = '{1}' AND ZONE_NAME = '{2}'".format(link.srcID, link.dstID, zoneName))

    def getAllLink(self):
        results = self.dbA.query("Link", " ID, ZONE_NAME, SRC_SWITCH_ID, " \
                                " DST_SWITCH_ID, TOTAL_BANDWIDTH, BANDWIDTH_UTILIZATION, PICKLE ")
        linkList = []
        for link in results:
            linkList.append(link)
        return linkList

    def updateLinksInAllZone(self, links):
        self._links = links

    def updateLinksByZone(self, links, zoneName):
        self._links[zoneName] = links

    def getLinksInAllZone(self):
        return self._links

    def getLinksByZone(self, zoneName):
        return self._links[zoneName]

    def getLink(self, srcID, dstID, zoneName):
        return self._links[zoneName][(srcID, dstID)]['link']

    def reserveLinkResource(self, srcID, dstID, reservedBandwidth, zoneName):
        if not self._linksReservedResources.has_key(zoneName):
            self._linksReservedResources[zoneName] = {}
        linkKey = (srcID, dstID)
        if not self._linksReservedResources[zoneName].has_key(linkKey):
            self._linksReservedResources[zoneName][linkKey] = {}
            self._linksReservedResources[zoneName][linkKey]["bandwidth"] = reservedBandwidth
        else:
            bandwidth = self._linksReservedResources[zoneName][linkKey]["bandwidth"]
            self._linksReservedResources[zoneName][linkKey]["bandwidth"] = bandwidth \
                + reservedBandwidth

    def releaseLinkResource(self, srcID, dstID, releaseBandwidth, zoneName):
        if not self._linksReservedResources.has_key(zoneName):
            self._linksReservedResources[zoneName] = {}
        linkKey = (srcID, dstID)
        if not self._linksReservedResources[zoneName].has_key(linkKey):
            raise ValueError("Unknown linkKey:{0}".format(linkKey))
        else:
            bandwidth = self._linksReservedResources[zoneName][linkKey]["bandwidth"]
            self._linksReservedResources[zoneName][linkKey]["bandwidth"] = bandwidth \
                - releaseBandwidth

    def getLinkReservedResource(self, srcID, dstID, zoneName):
        if not self._linksReservedResources.has_key(zoneName):
            self._linksReservedResources[zoneName] = {}
        linkKey = (srcID, dstID)
        if not self._linksReservedResources[zoneName].has_key(linkKey):
            # raise ValueError("Unknown linkKey:{0}".format(linkKey))
            self.reserveLinkResource(srcID, dstID, 0, zoneName)
        return self._linksReservedResources[zoneName][linkKey]["bandwidth"]

    def getLinkResidualResource(self, srcID, dstID, zoneName):
        reservedBandwidth = self.getLinkReservedResource(srcID, dstID, zoneName)
        link = self.getLink(srcID, dstID, zoneName)
        bandwidthCapacity = link.bandwidth
        residualBandwidth = bandwidthCapacity - reservedBandwidth
        return residualBandwidth

    def hasEnoughLinkResource(self, link, expectedBandwidth, zoneName):
        reservedBandwidth = self.getLinkReservedResource(
            link.srcID, link.dstID, zoneName)
        bandwidth = link.bandwidth
        residualBandwidth = bandwidth - reservedBandwidth
        # self.logger.debug(
        #     "link resource, bandwidth:{0}, reservedBandwidth:{1}, expectedBandwidth:{2}".format(
        #         bandwidth, reservedBandwidth,expectedBandwidth
        #     ))
        if residualBandwidth > expectedBandwidth:
            return True
        else:
            return False

    def getLinkUtil(self, link, zoneName):
        reservedBandwidth = self.getLinkReservedResource(
            link.srcID, link.dstID, zoneName)
        bandwidth = link.bandwidth
        return reservedBandwidth*1.0/bandwidth
