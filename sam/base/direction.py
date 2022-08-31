#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
Example:
    direction0 = {
        'ID': 0,
        'source': {"IPv4":"*", "node":None},
        'ingress': classifier,
        'match': {'srcIP': "*",'dstIP': WEBSITE_REAL_IP,
            'srcPort': "*",'dstPort': "*",'proto': "*"},
        'egress': classifier,
        'destination': {"IPv4": WEBSITE_REAL_IP, "node":None}
    }
'''

from typing import Union

from sam.base.switch import Switch
from sam.base.server import Server
from sam.base.sfcMatch import SFCMatch
from sam.base.trafficEndPoint import TrafficEndPoint
from sam.base.sfcConstant import SFC_DIRECTION_0, SFC_DIRECTION_1


class Direction(object):
    def __init__(self, id,      # type: Union[SFC_DIRECTION_0, SFC_DIRECTION_1]
                    source,     # type: TrafficEndPoint
                    destination, # type: TrafficEndPoint
                    match,      # type: SFCMatch
                    ingress,     # type: Union[Server, Switch]
                    egress      # type: Union[Server, Switch]
                ):
        self.id = id
        self.source = source
        self.ingress = ingress
        self.match = match
        self.egress = egress
        self.destination = destination

    def toDict(self):
        directionDict = {
            'ID': self.id,
            'source': self.source,
            'ingress': self.ingress,
            'match': self.match,
            'egress': self.egress,
            'destination': self.destination
        }
        return directionDict
