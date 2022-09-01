#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
The end point is either the traffic generator,
    or the traffic reciever.
'''

from typing import Union

from sam.base.switch import Switch
from sam.base.server import Server


class TrafficEndPoint(object):
    def __init__(self, node,         # type: Union[None, Server, Switch]
                    ipv4,            # type: str
                    ipv6=None,       # type: str
                    srv6=None,       # type: str
                    rocev1=None      # type: str
                ):
        self.node = node
        self.ipv4 = ipv4
        self.ipv6 = ipv6
        self.srv6 = srv6
        self.rocev1 = rocev1

    def toDict(self):
        return dict(
            (key, value)
            for (key, value) in self.__dict__.items()
            if value != None
            )

    def fromDict(self, dictionary):
        for key in list(self.__dict__.keys()):
            if key in dictionary:
                self.__dict__[key] = dictionary[key]
