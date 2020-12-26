#!/usr/bin/python
# -*- coding: UTF-8 -*-

SWITCH_TYPE_FORWARD = "SWITCH_TYPE_FORWARD"
SWITCH_TYPE_SFF = "SWITCH_TYPE_SFF"
SWITCH_TYPE_TOR = "SWITCH_TYPE_TOR"    # TODO: 建议用SWITCH_TYPE_SFF代替它
SWITCH_TYPE_DCNGATEWAY = "SWITCH_TYPE_DCNGATEWAY"

SWITCH_DEFAULT_TCAM_SIZE = 2000


class Switch(object):
    def __init__(self, switchID, switchType, lanNet=None, programmable=False,
        tcamSize=SWITCH_DEFAULT_TCAM_SIZE, tcamUsage=0):
        self.switchID = switchID
        self.switchType = switchType
        self.lanNet = lanNet
        self.programmable = programmable
        self.tcamSize = tcamSize
        self.tcamUsage = tcamUsage
        self.supportNF = []
        self.supportVNF = []

    def __str__(self):
        string = "{0}\n".format(self.__class__)
        for key,values in self.__dict__.items():
            string = string + "{0}:{1}\n".format(key, values)
        return string

    def __repr__(self):
        return str(self)
