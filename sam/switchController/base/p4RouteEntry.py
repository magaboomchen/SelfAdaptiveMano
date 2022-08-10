#!/usr/bin/python
# -*- coding: UTF-8 -*-

from sam.switchController.base.p4Match import P4Match
from sam.switchController.base.p4Action import P4Action


class P4RouteEntry(object):
    def __init__(self,
                 nodeID,    # type: int
                 match,     # type: P4Match
                 action     # type: P4Action
                 ):
        self.nodeID = nodeID
        self.match = match
        self.action = action
