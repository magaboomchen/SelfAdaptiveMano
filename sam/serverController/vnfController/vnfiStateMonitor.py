#!/usr/bin/python
# -*- coding: UTF-8 -*-

import ipaddress

from sam.base.monitorStatistic import MonitorStatistics, SrcDstPair
from sam.base.routingMorphic import IPV4_ROUTE_PROTOCOL, IPV6_ROUTE_PROTOCOL, \
                                    ROCEV1_ROUTE_PROTOCOL
from sam.base.server import Server
from sam.base.sfc import SFC_DIRECTION_0, SFC_DIRECTION_1
from sam.base.shellProcessor import ShellProcessor
from sam.base.vnf import VNF_TYPE_FW, VNF_TYPE_MONITOR, VNF_TYPE_RATELIMITER
from sam.serverController.vnfController.click.ControlSocket.controlSocket import ControlSocket


class VNFIStateMonitor(object):
    def __init__(self, logger):
        self.sP = ShellProcessor()
        self.cS = ControlSocket()
        self.logger = logger

    def monitorVNFIHandler(self, vnfi, vnfiDeployStatus):
        if vnfi.vnfType == VNF_TYPE_MONITOR:
            if type(vnfi.node) == Server:
                server = vnfi.node
                ipAddr = server.getControlNICIP()
                socketPort = vnfiDeployStatus.controlSocketPort
                commandName = "stat"
                mS = MonitorStatistics()
                for elementNamePrefix in ["ipv4_mon_direction", 
                                    "ipv6_mon_direction", 
                                    "rocev1_mon_direction"]:
                    for directionID in [SFC_DIRECTION_0, SFC_DIRECTION_1]:
                        elementName = elementNamePrefix + str(directionID)
                        stat = self.getStateFromMonitor(ipAddr, socketPort, elementName, commandName)
                        if elementNamePrefix == "ipv4_mon_direction":
                            routeProtocol = IPV4_ROUTE_PROTOCOL
                        elif elementNamePrefix == "ipv6_mon_direction":
                            routeProtocol = IPV6_ROUTE_PROTOCOL
                        elif elementNamePrefix == "rocev1_mon_direction":
                            routeProtocol = ROCEV1_ROUTE_PROTOCOL
                        else:
                            pass
                        formatedStatTupleList = self.parseRawMonitorStatData(stat, routeProtocol)
                        for formatedStat in formatedStatTupleList:
                            srcDstPair, pktRate, bytesRate = formatedStat
                            mS.addStatistic(directionID, srcDstPair, pktRate, bytesRate)
                self.logger.debug("mS is {0}".format(mS))
                return mS
            else:
                raise ValueError("Unknown vnfi's node type {0}".format(type(vnfi.node)))
        elif vnfi.vnfType == VNF_TYPE_FW:
            return vnfi.config
        elif vnfi.vnfType == VNF_TYPE_RATELIMITER:
            return vnfi.config
        else:
            return None

    def getStateFromMonitor(self, ipAddr, socketPort, elementName, commandName):
        return self.cS.readStateOfAnElement(ipAddr, socketPort, elementName, commandName)

    def parseRawMonitorStatData(self, stat, routeProtocol):
        self.logger.debug("routeProtocol {0}".format(routeProtocol))
        self.logger.debug("parseRawMonitorStatData is {0}".format(stat))
        stat = stat.strip('\n')
        statList = stat.splitlines()
        self.logger.debug("statList is {0}".format(statList))
        formatedStatTupleList = []
        for stat in statList:
            statList = stat.split(' ')
            src_high = int(statList[0])
            src_low = int(statList[1])
            src = (src_high<<64) + src_low
            dst_high = int(statList[2])
            dst_low = int(statList[3])
            dst = (dst_high<<64) + dst_low
            pktRate = int(statList[4])
            bytesRate = int(statList[5])

            if routeProtocol == IPV4_ROUTE_PROTOCOL:
                src = ipaddress.IPv4Address(src)
                dst = ipaddress.IPv4Address(dst)
            else:
                src = ipaddress.IPv6Address(src)
                dst = ipaddress.IPv6Address(dst)
            srcDstPair = SrcDstPair(src, dst, routeProtocol)
            formatedStatTupleList.append((srcDstPair, pktRate, bytesRate))
        return formatedStatTupleList
