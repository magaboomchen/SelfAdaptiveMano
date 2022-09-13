#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.switchController.base.p4Match import P4Match
from sam.switchController.base.p4Action import P4Action


class P4ClassifierEntry(object):
    def __init__(self,
                 nodeID,    # type: int
                 match,     # type: P4Match
                 action     # type: P4Action
                 ):
        self.nodeID = nodeID    # SFC->directions->ingress&egress
        self.match = match
        self.action = action

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)
