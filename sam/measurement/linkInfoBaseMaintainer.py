#!/usr/bin/python
# -*- coding: UTF-8 -*-

from typing import Any, Dict, Tuple, Union

from sam.base.xibMaintainer import XInfoBaseMaintainer
from sam.base.messageAgent import SIMULATOR_ZONE, TURBONET_ZONE


class LinkInfoBaseMaintainer(XInfoBaseMaintainer):
    def __init__(self):
        super(LinkInfoBaseMaintainer, self).__init__()
        self._links = {}    # type: Dict[Union[TURBONET_ZONE, SIMULATOR_ZONE], Dict[Tuple(int,int), Dict[str, Any]]]
        # [zoneName][(srcID,dstID)] = {'link':link, 'Active':True, 'Status':none}
        self._linksReservedResources = {}
        self.isLinkInfoInDB = False

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
        self.isLinkInfoInDB = True

    def hasLink(self, srcID, dstID, zoneName):
        if self.isLinkInfoInDB:
            results = self.dbA.query("Link", " SRC_SWITCH_ID, DST_SWITCH_ID ",
                        " SRC_SWITCH_ID = '{0}' AND DST_SWITCH_ID = '{1}' AND ZONE_NAME = '{2}'".format(srcID, dstID, zoneName))
            if results != ():
                return True
            else:
                return False
        else:
            if (srcID, dstID) in self._links[zoneName].keys():
                return True
            else:
                return False

    def addLink(self, link, zoneName):
        if self.isLinkInfoInDB:
            if not self.hasLink(link.srcID, link.dstID, zoneName):
                self.dbA.insert("Link",
                    " ZONE_NAME, SRC_SWITCH_ID, DST_SWITCH_ID, TOTAL_BANDWIDTH," \
                    " BANDWIDTH_UTILIZATION, PICKLE ",
                        (
                            zoneName,
                            link.srcID,
                            link.dstID,
                            link.bandwidth,
                            link.utilization,
                            self.pIO.obj2Pickle(link)
                        )
                    )
        else:
            linkID = link.linkID
            self._links[zoneName][linkID] = {'link':link, 'Active':True, 'Status':None}

    def delLink(self, link, zoneName):
        if self.isLinkInfoInDB:
            if self.hasLink(link.srcID, link.dstID, zoneName):
                condition = " SRC_SWITCH_ID = {0} AND DST_SWITCH_ID = {1} AND ZONE_NAME = '{2}'".format(link.srcID, link.dstID, zoneName)
                self.dbA.delete("Link", condition)
        else:
            del self._links[zoneName][(link.srcID, link.dstID)]

    def getAllLink(self):
        linkList = []
        if self.isLinkInfoInDB:
            results = self.dbA.query("Link", " ID, ZONE_NAME, SRC_SWITCH_ID, " \
                                    " DST_SWITCH_ID, TOTAL_BANDWIDTH, BANDWIDTH_UTILIZATION, PICKLE ")
            for link in results:
                linkList.append(link)
        else:
            for zoneName, linksInfo in self._links.items():
                for linkID, linkInfo in linksInfo.items():
                    linkList.append(linkInfo['link'])
        return linkList

    def updateLinksInAllZone(self, links):
        self._links = links

    def updateLinksByZone(self, links, zoneName):
        self._links[zoneName] = links

    def updateLinkState(self, linkID, zoneName, state):
        self._links[zoneName][(linkID[0], linkID[1])]['Active'] = state

    def getLinksInAllZone(self):
        return self._links

    def getLinksByZone(self, zoneName, pruneInactiveLinks=False):
        if pruneInactiveLinks:
            links = {}
            for linkID, linkInfoDict in self._links[zoneName].items():
                if linkInfoDict['Active']:
                    links[linkID] = linkInfoDict
            return links
        else:
            return self._links[zoneName]

    def getLink(self, srcID, dstID, zoneName):
        return self._links[zoneName][(srcID, dstID)]['link']

    def reserveLinkResource(self, srcID, dstID, reservedBandwidth, zoneName):
        if not (zoneName in self._linksReservedResources):
            self._linksReservedResources[zoneName] = {}
        linkKey = (srcID, dstID)
        if not (linkKey in self._linksReservedResources[zoneName]):
            self._linksReservedResources[zoneName][linkKey] = {}
            self._linksReservedResources[zoneName][linkKey]["bandwidth"] = reservedBandwidth
        else:
            bandwidth = self._linksReservedResources[zoneName][linkKey]["bandwidth"]
            self._linksReservedResources[zoneName][linkKey]["bandwidth"] = bandwidth \
                + reservedBandwidth

    def releaseLinkResource(self, srcID, dstID, releaseBandwidth, zoneName):
        if not (zoneName in self._linksReservedResources):
            self._linksReservedResources[zoneName] = {}
        linkKey = (srcID, dstID)
        if not (linkKey in self._linksReservedResources[zoneName]):
            raise ValueError("Unknown linkKey:{0}".format(linkKey))
        else:
            bandwidth = self._linksReservedResources[zoneName][linkKey]["bandwidth"]
            self._linksReservedResources[zoneName][linkKey]["bandwidth"] = bandwidth \
                - releaseBandwidth

    def getLinkReservedResource(self, srcID, dstID, zoneName):
        if not (zoneName in self._linksReservedResources):
            self._linksReservedResources[zoneName] = {}
        linkKey = (srcID, dstID)
        if not (linkKey in self._linksReservedResources[zoneName]):
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
