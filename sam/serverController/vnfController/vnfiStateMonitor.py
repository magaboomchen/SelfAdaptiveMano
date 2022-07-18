#!/usr/bin/python
# -*- coding: UTF-8 -*-


from sam.base.server import Server
from sam.base.shellProcessor import ShellProcessor
from sam.base.vnf import VNF_TYPE_FORWARD, VNF_TYPE_FW, VNF_TYPE_MONITOR, VNF_TYPE_RATELIMITER
from sam.serverController.vnfController.click.ControlSocket.controlSocket import ControlSocket


class VNFIStateMonitor(object):
    def __init__(self):
        self.sP = ShellProcessor()
        self.cS = ControlSocket()

    def monitorVNFIHandler(self, vnfi, vnfiDeployStatus):
        if vnfi.vnfType == VNF_TYPE_MONITOR:
            if type(vnfi.node) == Server:
                server = vnfi.node
                ipAddr = server.getControlNICIP()
                socketPort = vnfiDeployStatus.controlSocketPort
                commandName = "stat"
                flowStatisticsDict = {}
                for elementName in ["ipv4_mon_direction0", "ipv4_mon_direction1",
                                    "ipv6_mon_direction0", "ipv6_mon_direction1",
                                    "rocev1_mon_direction0", "rocev1_mon_direction1"]:
                    stat = self.getStateFromMonitor(ipAddr, socketPort, elementName, commandName)
                    flowStatisticsDict.update({elementName: stat})
                return {"FlowStatisticsDict":flowStatisticsDict}
            else:
                raise ValueError("Unknown vnfi's node type {0}".format(type(vnfi.node)))
        elif vnfi.vnfType == VNF_TYPE_FW:
            return {"FWRulesNum":len(vnfi.config)}
        elif vnfi.vnfType == VNF_TYPE_RATELIMITER:
            return {"rateLimitition":vnfi.config.maxMbps}
        else:
            return None

    def getStateFromMonitor(self, ipAddr, socketPort, elementName, commandName):
        return self.cS.readStateOfAnElement(ipAddr, socketPort, elementName, commandName)
