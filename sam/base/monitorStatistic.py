#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This file defines the format of monitor's statistics
'''

import ipaddress
from typing import Union

from sam.base.routingMorphic import IPV4_ROUTE_PROTOCOL
from sam.base.routingMorphic import IPV6_ROUTE_PROTOCOL
from sam.base.routingMorphic import SRV6_ROUTE_PROTOCOL
from sam.base.routingMorphic import ROCEV1_ROUTE_PROTOCOL
from sam.base.sfc import SFC_DIRECTION_0, SFC_DIRECTION_1


class SrcDstPair(object):
    def __init__(self, src, dst, routeProtocol):
        # type: (Union[ipaddress.IPv4Address, ipaddress.IPv6Address], Union[ipaddress.IPv4Address, ipaddress.IPv6Address], Union[IPV4_ROUTE_PROTOCOL, IPV6_ROUTE_PROTOCOL, SRV6_ROUTE_PROTOCOL, ROCEV1_ROUTE_PROTOCOL]) -> None
        self.src = src
        self.dst = dst
        self.routeProtocol = routeProtocol

    def __hash__(self):
        return hash((int(self.src), int(self.dst)))

    def __eq__(self, other):
        return (int(self.src), int(self.dst), self.routeProtocol) \
                    == (int(other.src), int(other.dst), other.routeProtocol)

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)


class MonitorStatistics(object):
    def __init__(self):
        self.ipv4Direction = {SFC_DIRECTION_0:{}, SFC_DIRECTION_1:{}}
        self.ipv6Direction = {SFC_DIRECTION_0:{}, SFC_DIRECTION_1:{}}
        self.srv6Direction = {SFC_DIRECTION_0:{}, SFC_DIRECTION_1:{}}
        self.rocev1Direction = {SFC_DIRECTION_0:{}, SFC_DIRECTION_1:{}}

    def addStatistic(self, directionID, srcDstPair, pktRate, bytesRate):
        # type: (Union[SFC_DIRECTION_0,SFC_DIRECTION_1], SrcDstPair, int, int) -> None
        routeProtocol = srcDstPair.routeProtocol
        if routeProtocol == IPV4_ROUTE_PROTOCOL:
            self.ipv4Direction[directionID][srcDstPair] = (pktRate, bytesRate)
        elif routeProtocol == IPV6_ROUTE_PROTOCOL:
            self.ipv6Direction[directionID][srcDstPair] = (pktRate, bytesRate)
        elif routeProtocol == SRV6_ROUTE_PROTOCOL:
            self.srv6Direction[directionID][srcDstPair] = (pktRate, bytesRate)
        elif routeProtocol == ROCEV1_ROUTE_PROTOCOL:
            self.rocev1Direction[directionID][srcDstPair] = (pktRate, bytesRate)
        else:
            raise ValueError("Unknown route protocol {0}".format(routeProtocol))

    def getPktBytesRateStatisticDict(self, directionID, routeProtocol):
        # type: (Union[SFC_DIRECTION_0,SFC_DIRECTION_1], Union[IPV4_ROUTE_PROTOCOL, IPV6_ROUTE_PROTOCOL, SRV6_ROUTE_PROTOCOL, ROCEV1_ROUTE_PROTOCOL]) -> dict[SrcDstPair, (int, int)]
        if routeProtocol == IPV4_ROUTE_PROTOCOL:
            return self.ipv4Direction[directionID]
        elif routeProtocol == IPV6_ROUTE_PROTOCOL:
            return self.ipv6Direction[directionID]
        elif routeProtocol == SRV6_ROUTE_PROTOCOL:
            return self.srv6Direction[directionID]
        elif routeProtocol == ROCEV1_ROUTE_PROTOCOL:
            return self.rocev1Direction[directionID]
        else:
            raise ValueError("Unknown route protocol {0}".format(routeProtocol))

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)


if __name__ == "__main__":
    sDP = SrcDstPair(ipaddress.IPv4Address("1.1.1.1"), 
                ipaddress.IPv4Address("1.1.1.2"),
                IPV4_ROUTE_PROTOCOL
                )

    mS = MonitorStatistics()
    mS.addStatistic(0, sDP, 1, 1)
    res = mS.getPktBytesRateStatisticDict(SFC_DIRECTION_0, IPV4_ROUTE_PROTOCOL)
    print(res)